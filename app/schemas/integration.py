"""
Integration schemas for chat configs
Supports multiple providers and multiple resource types per provider
Integrations is an array to support multiple providers
"""
from typing import Optional, Literal, List, Union
from pydantic import BaseModel, Field


# Google Integration Resource Types
class GoogleSheetsConfig(BaseModel):
    """Google Sheets configuration"""
    type: Literal["sheets"] = "sheets"
    sheet_id: str = Field(..., description="Google Sheet ID")
    sheet_name: Optional[str] = Field(None, description="Google Sheet name")


class GooglePDFsConfig(BaseModel):
    """Google PDFs configuration"""
    type: Literal["pdfs"] = "pdfs"
    pdf_id: str = Field(..., description="Google PDF ID")
    pdf_name: Optional[str] = Field(None, description="Google PDF name")


# Google Integration
class GoogleIntegration(BaseModel):
    """Google integration configuration"""
    provider: Literal["google"] = "google"
    enable: bool = Field(True, description="Whether integration is enabled")
    resources: dict = Field(
        default_factory=lambda: {"sheets": None, "pdfs": None},
        description="Google resource configurations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "google",
                "enable": True,
                "resources": {
                    "sheets": {
                        "type": "sheets",
                        "sheet_id": "1abc123...",
                        "sheet_name": "My Sheet"
                    },
                    "pdfs": {
                        "type": "pdfs",
                        "pdf_id": "1xyz789...",
                        "pdf_name": "My PDF"
                    }
                }
            }
        }


# Union type for all integrations
Integration = GoogleIntegration


def normalize_integrations(integrations: Optional[List[dict]]) -> Optional[List[dict]]:
    """
    Normalize integrations format (validate structure)
    Returns array of integrations
    """
    if not integrations:
        return None

    if not isinstance(integrations, list):
        return None

    # Normalize each integration in the list
    normalized = []
    for integration in integrations:
        if integration:
            normalized_item = normalize_integration(integration)
            if normalized_item:
                normalized.append(normalized_item)

    return normalized if normalized else None


def normalize_integration(integration: Optional[dict]) -> Optional[dict]:
    """
    Normalize single integration format (validate structure)
    """
    if not integration:
        return None

    if not isinstance(integration, dict):
        return None

    # Validate and normalize structure
    if integration.get("provider") == "google":
        # Ensure resources object exists
        if "resources" not in integration:
            integration["resources"] = {"sheets": None, "pdfs": None}

        # Ensure resources.sheets and resources.pdfs exist
        if "sheets" not in integration["resources"]:
            integration["resources"]["sheets"] = None
        if "pdfs" not in integration["resources"]:
            integration["resources"]["pdfs"] = None

        # Validate sheets config if exists
        if integration["resources"]["sheets"]:
            sheets = integration["resources"]["sheets"]
            if not isinstance(sheets, dict):
                integration["resources"]["sheets"] = None
            elif "sheet_id" not in sheets:
                integration["resources"]["sheets"] = None

        # Validate pdfs config if exists
        if integration["resources"]["pdfs"]:
            pdfs = integration["resources"]["pdfs"]
            if not isinstance(pdfs, dict):
                integration["resources"]["pdfs"] = None
            elif "pdf_id" not in pdfs:
                integration["resources"]["pdfs"] = None

    return integration

