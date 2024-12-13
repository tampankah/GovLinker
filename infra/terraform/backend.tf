terraform {
  backend "gcs" {
    bucket = "terraform-state-bucket-government-assistant-001" 
    prefix = "terraform/state"
  }
}
