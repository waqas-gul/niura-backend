# models.py
from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, String, Boolean, Date
from sqlalchemy.sql import func
from app.database import Base  

class EarbudUUID(Base):
    __tablename__ = "Earbud_UUIDs"

    ID = Column(Integer, primary_key=True, index=True)
    
    # UUID fields
    Left_Service_UUID = Column(Text)
    Left_RX_UUID = Column(Text)
    Left_TX_UUID = Column(Text)
    Right_Service_UUID = Column(Text)
    Right_RX_UUID = Column(Text)
    Right_TX_UUID = Column(Text)
    
    # New hardware identification fields (using lowercase as PostgreSQL converts them)
    Serial_Number = Column("serial_number", String(50), nullable=True, comment="Shared serial number for both earbuds")
    
    # Left earbud specific fields (using lowercase column names)
    Left_MAC_Address = Column("left_mac_address", String(17), nullable=True, comment="MAC address format: XX:XX:XX:XX:XX:XX")
    Left_Firmware_Upload = Column("left_firmware_upload", Boolean, default=False, comment="Firmware upload status")
    Left_Firmware_Version_EEG = Column("left_firmware_version_eeg", String(20), nullable=True, comment="EEG firmware version")
    Left_Firmware_Version_Audio = Column("left_firmware_version_audio", String(20), nullable=True, comment="Audio firmware version")
    Left_Last_Upload_Date = Column("left_last_upload_date", Date, nullable=True, comment="Last firmware upload date")
    Left_Deployment_Status = Column("left_deployment_status", String(100), nullable=True, comment="Current deployment status")
    Left_Comments = Column("left_comments", Text, nullable=True, comment="Additional comments or notes")
    
    # Right earbud specific fields (using lowercase column names)
    Right_MAC_Address = Column("right_mac_address", String(17), nullable=True, comment="MAC address format: XX:XX:XX:XX:XX:XX")
    Right_Firmware_Upload = Column("right_firmware_upload", Boolean, default=False, comment="Firmware upload status")
    Right_Firmware_Version_EEG = Column("right_firmware_version_eeg", String(20), nullable=True, comment="EEG firmware version")  
    Right_Firmware_Version_Audio = Column("right_firmware_version_audio", String(20), nullable=True, comment="Audio firmware version")
    Right_Last_Upload_Date = Column("right_last_upload_date", Date, nullable=True, comment="Last firmware upload date")
    Right_Deployment_Status = Column("right_deployment_status", String(100), nullable=True, comment="Current deployment status")
    Right_Comments = Column("right_comments", Text, nullable=True, comment="Additional comments or notes")
    
    # User association
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
