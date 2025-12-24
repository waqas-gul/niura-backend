# schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import date
import re

class EarbudUUIDBase(BaseModel):
    # UUID fields
    Left_Service_UUID: Optional[str] = None
    Left_RX_UUID: Optional[str] = None
    Left_TX_UUID: Optional[str] = None
    Right_Service_UUID: Optional[str] = None
    Right_RX_UUID: Optional[str] = None
    Right_TX_UUID: Optional[str] = None
    
    # Hardware identification
    Serial_Number: Optional[str] = Field(None, max_length=50, description="Shared serial number for both earbuds")
    
    # Left earbud fields
    Left_MAC_Address: Optional[str] = Field(None, pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', description="MAC address in XX:XX:XX:XX:XX:XX format")
    Left_Firmware_Upload: Optional[bool] = False
    Left_Firmware_Version_EEG: Optional[str] = Field(None, max_length=20)
    Left_Firmware_Version_Audio: Optional[str] = Field(None, max_length=20)
    Left_Last_Upload_Date: Optional[date] = None
    Left_Deployment_Status: Optional[str] = Field(None, max_length=100)
    Left_Comments: Optional[str] = None
    
    # Right earbud fields
    Right_MAC_Address: Optional[str] = Field(None, pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', description="MAC address in XX:XX:XX:XX:XX:XX format")
    Right_Firmware_Upload: Optional[bool] = False
    Right_Firmware_Version_EEG: Optional[str] = Field(None, max_length=20)
    Right_Firmware_Version_Audio: Optional[str] = Field(None, max_length=20)
    Right_Last_Upload_Date: Optional[date] = None
    Right_Deployment_Status: Optional[str] = Field(None, max_length=100)
    Right_Comments: Optional[str] = None
    
    # User association
    user_id: int

    @validator('Left_MAC_Address', 'Right_MAC_Address')
    def validate_mac_address(cls, v):
        if v is not None and not v:
            return None
        return v
    
    @validator('Left_Service_UUID', 'Left_RX_UUID', 'Left_TX_UUID', 
               'Right_Service_UUID', 'Right_RX_UUID', 'Right_TX_UUID')
    def validate_uuid_format(cls, v):
        """Validate and normalize UUID format - accepts standard UUID format"""
        if v is None or not v:
            return None
        
        # Standard UUID pattern: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        
        if re.match(uuid_pattern, v):
            return v.lower()  # Normalize to lowercase
        
        raise ValueError(f'Invalid UUID format: {v}. Expected format: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX')


class EarbudUUIDCreate(EarbudUUIDBase):
    pass

class EarbudUUIDUpdate(BaseModel):
    # UUID fields
    Left_Service_UUID: Optional[str] = None
    Left_RX_UUID: Optional[str] = None
    Left_TX_UUID: Optional[str] = None
    Right_Service_UUID: Optional[str] = None
    Right_RX_UUID: Optional[str] = None
    Right_TX_UUID: Optional[str] = None
    
    # Hardware identification
    Serial_Number: Optional[str] = None
    
    # Left earbud fields
    Left_MAC_Address: Optional[str] = None
    Left_Firmware_Upload: Optional[bool] = None
    Left_Firmware_Version_EEG: Optional[str] = None
    Left_Firmware_Version_Audio: Optional[str] = None
    Left_Last_Upload_Date: Optional[date] = None
    Left_Deployment_Status: Optional[str] = None
    Left_Comments: Optional[str] = None
    
    # Right earbud fields
    Right_MAC_Address: Optional[str] = None
    Right_Firmware_Upload: Optional[bool] = None
    Right_Firmware_Version_EEG: Optional[str] = None
    Right_Firmware_Version_Audio: Optional[str] = None
    Right_Last_Upload_Date: Optional[date] = None
    Right_Deployment_Status: Optional[str] = None
    Right_Comments: Optional[str] = None
    
    # User ID for bulk updates
    user_id: Optional[int] = None

class EarbudUUIDResponse(EarbudUUIDBase):
    ID: int

    class Config:
        orm_mode = True
