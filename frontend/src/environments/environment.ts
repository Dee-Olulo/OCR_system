// frontend/src/environments/environment.ts

export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',

  
  // n8n production webhook base URL.
  // The Angular app POSTs to this after every successful file upload
  // to trigger the invoice processing pipeline.
  //
  // This must point to the PRODUCTION webhook URL (not the test URL).
  // The production URL is only active when the n8n workflow is Activated
  // (green toggle in the top-right of the workflow editor).
  //
  // Format: http://localhost:5678/webhook/YOUR_CHOSEN_PATH
  // The path "ocr-invoice-process" must match what you set in the
  // n8n Webhook Trigger node → Path field.
  n8nWebhookUrl: 'http://localhost:5678/webhook/ocr-invoice-process',

  // Must match the value you set in the n8n Webhook Trigger node → Header Auth credential.
  n8nWebhookSecret: '3d276301c2e24c755717126108dca6074980dca3f583aefece25fe0a2324cc68'

};