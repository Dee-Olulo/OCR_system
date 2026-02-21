import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class LineItem:
    line_number:  Optional[int]   = None
    tariff_code:  Optional[str]   = None
    description:  Optional[str]   = None
    date:         Optional[str]   = None
    quantity:     Optional[float] = None
    unit_price:   Optional[float] = None
    amount:       Optional[float] = None
    # Internal — stripped before API output
    _all_amounts: list            = field(default_factory=list, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_all_amounts", None)
        return d


@dataclass
class TableResult:
    line_items:     list
    claimed_total:  Optional[float]
    computed_total: Optional[float]
    total_match:    bool
    discrepancies:  list[str]
    table_detected: bool
    confidence:     float          # 0.0 – 1.0


# ── Compiled patterns ─────────────────────────────────────────────────────────

# Row that starts with a 1–2 digit line number
_LINE_START = re.compile(r"^(\d{1,2})\s+")

# Numeric tariff / procedure code (4–6 digits, not a date/amount)
_TARIFF_CODE = re.compile(r"\b(\d{4,6})\b")

# Date:  DD/MM/YYYY  DD/MM/YY  DD-MM-YYYY  YYYY-MM-DD
# Intentionally catches partial OCR split "26/01/202" (last digit on next line)
_DATE = re.compile(r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{2,4})\b")

# Decimal amounts: 1,234.56 or 1234.56
_AMOUNT = re.compile(r"\b([\d]{1,3}(?:,\d{3})*\.\d{2})\b")

# Small integer for quantity — applied only within the pre-date segment
_QTY = re.compile(r"\b([1-9]\d?)\b")

# Header line: must hit ≥ 2 of these keywords to count as a table header
_HEADER_KEYWORDS = re.compile(
    r"\b(LINE|TARIFF|DESCRIPTION|QTY|QUANTITY|UNIT|PRICE|AMOUNT|DATE|TOOTH|SERVICE)\b",
    re.IGNORECASE,
)

# Total / subtotal rows
_TOTAL_ROW = re.compile(
    r"^\s*(?:total|sub[\-\s]?total|grand\s+total|amount\s+due|balance)",
    re.IGNORECASE,
)

# Rows that are purely numeric separators / summary lines
_NUMERIC_ROW = re.compile(r"^[\d\s\|,\.]+$")


# ── Main service class ────────────────────────────────────────────────────────

class TableExtractor:
    """
    Extract line items from OCR text using structure-aware heuristics.

    Works across different invoice layouts without hardcoding column
    positions or field names. The only structural assumption is that
    each line item begins with a 1–2 digit row number.
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def extract(self, ocr_text: str) -> TableResult:
        """
        Full extraction pipeline.

        Args:
            ocr_text: Raw text from OCR engine.

        Returns:
            TableResult with line_items and arithmetic validation.
        """
        lines = [l.rstrip() for l in ocr_text.splitlines()]

        table_lines, header_line = self._detect_table(lines)

        if not table_lines:
            logger.info("No table detected in OCR text")
            return TableResult(
                line_items=[],
                claimed_total=None,
                computed_total=None,
                total_match=False,
                discrepancies=["No line-item table detected in document"],
                table_detected=False,
                confidence=0.0,
            )

        logger.info(f"Table detected: {len(table_lines)} rows | header: {header_line!r}")

        merged_rows = self._merge_continuations(table_lines)
        claimed_total = self._extract_claimed_total(merged_rows)
        item_rows = [r for r in merged_rows if self._is_item_row(r)]
        line_items = [self._parse_item_row(row) for row in item_rows]
        line_items = [li for li in line_items if li is not None]

        computed_total, total_match, discrepancies = self._validate(line_items, claimed_total)
        confidence = self._score_confidence(line_items, total_match)

        logger.info(
            f"Extracted {len(line_items)} items | "
            f"total_match={total_match} | confidence={confidence:.2f}"
        )

        return TableResult(
            line_items=line_items,
            claimed_total=claimed_total,
            computed_total=computed_total,
            total_match=total_match,
            discrepancies=discrepancies,
            table_detected=True,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Step 1 — Table detection
    # ------------------------------------------------------------------

    def _detect_table(self, lines: list[str]) -> tuple[list[str], str]:
        """
        Find the block of lines containing the billing table.

        Scans for a header line with ≥ 2 table-related keywords, then
        collects rows until two consecutive blanks or a clearly non-table
        section appears.
        """
        header_idx = None
        for i, line in enumerate(lines):
            if len(_HEADER_KEYWORDS.findall(line)) >= 2:
                header_idx = i
                break

        if header_idx is None:
            return [], ""

        header_text = lines[header_idx]
        table_lines = []
        blank_streak = 0

        for line in lines[header_idx + 1:]:
            stripped = line.strip()

            if not stripped:
                blank_streak += 1
                if blank_streak >= 2:
                    break
                continue

            blank_streak = 0

            if re.match(
                r"^(ICD|DIAGNOSIS|COUNCIL|DOCTOR'?S?\s+SIGN|AUTHORIS)",
                stripped, re.IGNORECASE
            ):
                break

            table_lines.append(stripped)

        return table_lines, header_text

    # ------------------------------------------------------------------
    # Step 2 — Continuation line merging
    # ------------------------------------------------------------------

    def _merge_continuations(self, lines: list[str]) -> list[str]:
        """
        OCR wraps long descriptions or split date digits across lines.

        A row starting with a 1–2 digit number = new item.
        Subsequent rows without that pattern are continuation lines and
        are appended to the previous row.
        Purely-numeric summary rows are kept standalone.
        """
        merged: list[str] = []

        for line in lines:
            if not line:
                continue

            if _TOTAL_ROW.match(line) or _NUMERIC_ROW.match(line):
                merged.append(line)
                continue

            if _LINE_START.match(line):
                merged.append(line)
            elif merged:
                merged[-1] = merged[-1] + " " + line

        return merged

    # ------------------------------------------------------------------
    # Step 3 — Claimed total extraction
    # ------------------------------------------------------------------

    def _extract_claimed_total(self, rows: list[str]) -> Optional[float]:
        """
        Find the grand total from the last summary / purely-numeric row.
        Returns the largest decimal amount in that row.
        """
        for row in reversed(rows):
            if _TOTAL_ROW.match(row) or _NUMERIC_ROW.match(row):
                amounts = [float(a.replace(",", "")) for a in _AMOUNT.findall(row)]
                if amounts:
                    return max(amounts)
        return None

    # ------------------------------------------------------------------
    # Step 4 — Item row detection and parsing
    # ------------------------------------------------------------------

    def _is_item_row(self, row: str) -> bool:
        return bool(_LINE_START.match(row)) and not _TOTAL_ROW.match(row)

    def _parse_item_row(self, row: str) -> Optional[LineItem]:
        """
        Parse one (possibly merged) item row into a LineItem.

        Extraction order:
        1. Line number  — leading digits
        2. Tariff code  — 4–6 digit code immediately after line number
        3. Date         — first date pattern; fixes OCR-split years by
                          looking for a trailing lone digit at the END of
                          the full post-date string (not immediately after
                          the date, which would grab the leading digit of
                          an amount like "6,670.00" instead).
        4. Quantity     — lone small int in the PRE-DATE segment only
                          (prevents split-date digits from being read as qty)
        5. Amounts      — all decimals in the post-date segment
        6. Description  — remaining words pre-date + continuation words
                          after stripping amounts from post-date
        7. unit_price / amount — first / third amount, following the
                          standard column order:
                          UNIT PRICE | FEE CHARGED | AWARD | SHORTFALL | EXCESS
        """
        try:
            item = LineItem()

            # 1. Line number
            ln_m = _LINE_START.match(row)
            item.line_number = int(ln_m.group(1)) if ln_m else None
            rest = row[ln_m.end():] if ln_m else row

            # 2. Tariff code
            tc_m = _TARIFF_CODE.search(rest)
            item.tariff_code = tc_m.group(1) if tc_m else None
            after_tc = rest[tc_m.end():].lstrip(" |") if tc_m else rest

            # 3. Date
            date_m = _DATE.search(after_tc)
            raw_date  = date_m.group(1) if date_m else None
            pre_date  = after_tc[:date_m.start()] if date_m else after_tc
            post_date = after_tc[date_m.end():]   if date_m else ""

            # Fix OCR-split year: year has only 3 digits ("26/01/202") and
            # there's a lone digit at the very end of the post_date string
            # ("...RANDOM 6").  We look at the END — not immediately after
            # the date — to avoid consuming the leading "6" of "6,670.00".
            if raw_date:
                year_part = re.split(r"[/\-]", raw_date)[-1]
                if len(year_part) == 3:
                    eol_digit = re.search(r"\b(\d)\s*$", post_date.strip())
                    if eol_digit:
                        raw_date = raw_date + eol_digit.group(1)
                        # Remove the trailing digit from post_date so it
                        # isn't treated as a continuation word or amount
                        post_date = post_date[:post_date.rfind(eol_digit.group(1))].rstrip()

            item.date = raw_date

            # 4. Quantity — pre-date segment only
            qty_m = _QTY.search(pre_date)
            if qty_m:
                item.quantity = float(qty_m.group(1))
                pre_date = pre_date[:qty_m.start()] + pre_date[qty_m.end():]

            # 5. Amounts — post-date segment
            raw_amounts = _AMOUNT.findall(post_date)
            amounts = [float(a.replace(",", "")) for a in raw_amounts]
            item._all_amounts = amounts

            # 6. Description — pre-date words + continuation words in post-date
            post_no_amounts = _AMOUNT.sub("", post_date)
            continuation = re.sub(r"[\|\s]+", " ", post_no_amounts).strip()
            desc = re.sub(r"[\|\s]+", " ", pre_date).strip()
            if continuation:
                desc = (desc + " " + continuation).strip()
            desc = re.sub(r"\s{2,}", " ", desc).strip("/ ,").strip()
            item.description = desc if desc else None

            # 7. Amount columns
            #    UNIT PRICE | FEE CHARGED | AWARD | SHORTFALL | EXCESS
            if len(amounts) >= 1:
                item.unit_price = amounts[0]
            if len(amounts) >= 3:
                item.amount = amounts[2]   # AWARD column
            elif len(amounts) == 2:
                item.amount = amounts[1]
            elif len(amounts) == 1:
                item.amount = amounts[0]

            return item

        except Exception as e:
            logger.warning(f"Failed to parse row: {row!r} | {e}")
            return None

    # ------------------------------------------------------------------
    # Step 5 — Arithmetic validation
    # ------------------------------------------------------------------

    def _validate(
        self,
        items: list,
        claimed_total: Optional[float],
    ) -> tuple[Optional[float], bool, list[str]]:
        """
        Two validation checks:
        1. Sum of line item amounts == claimed_total
        2. Per-item: quantity × unit_price ≈ amount (when quantity is known)
        """
        discrepancies: list[str] = []

        awarded = [li.amount for li in items if li.amount is not None]
        computed_total = round(sum(awarded), 2) if awarded else None
        total_match = False

        if computed_total is not None and claimed_total is not None:
            diff = abs(computed_total - claimed_total)
            total_match = diff < 0.02
            if not total_match:
                discrepancies.append(
                    f"Total mismatch: computed {computed_total:.2f} "
                    f"≠ claimed {claimed_total:.2f} (Δ {diff:.2f})"
                )
        elif claimed_total is None:
            discrepancies.append("No claimed total found — cannot verify sum")
        elif computed_total is None:
            discrepancies.append("No line item amounts extracted — cannot verify sum")

        for li in items:
            if li.quantity and li.unit_price and li.amount:
                expected = round(li.quantity * li.unit_price, 2)
                if abs(expected - li.amount) > 0.02:
                    discrepancies.append(
                        f"Line {li.line_number}: "
                        f"qty({li.quantity}) × unit({li.unit_price:.2f}) "
                        f"= {expected:.2f} ≠ amount({li.amount:.2f})"
                    )

        return computed_total, total_match, discrepancies

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------

    def _score_confidence(self, items: list, total_match: bool) -> float:
        """
        Heuristic confidence 0.0–1.0 based on field population and total check.
        """
        if not items:
            return 0.0

        n = len(items)
        has_desc   = sum(1 for li in items if li.description) / n
        has_amount = sum(1 for li in items if li.amount)      / n
        has_tariff = sum(1 for li in items if li.tariff_code) / n
        total_bonus = 0.2 if total_match else 0.0

        return round(
            min(has_desc * 0.3 + has_amount * 0.3 + has_tariff * 0.2 + total_bonus, 1.0),
            2
        )


# ── Module-level singleton ────────────────────────────────────────────────────

table_extractor = TableExtractor()