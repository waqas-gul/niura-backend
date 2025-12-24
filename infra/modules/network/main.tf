########################################
# 🧩 VARIABLES
########################################

# These variables will be filled from your .tfvars file (like envs/production.tfvars)
variable "project_name" {}   # e.g., "niura"
variable "environment" {}    # e.g., "production" or "staging"


########################################
# 🌐 VPC (Virtual Private Cloud)
########################################

# This creates your own isolated virtual network in AWS where all your services will live.
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"    # Defines the internal IP address range for your VPC.
  enable_dns_support   = true             # Enables internal DNS resolution inside your VPC.
  enable_dns_hostnames = true             # Allows AWS to assign DNS hostnames to instances.

  tags = {
    # Gives a friendly name to your VPC, like "niura-production-vpc"
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}


########################################
# 🧱 SUBNET (Public Sub-network)
########################################

# A subnet divides your VPC into smaller networks. 
# Here we’re creating a *public subnet* — resources here can have public IPs and connect to the Internet.
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id         # Connects this subnet to your main VPC.
  cidr_block              = "10.0.1.0/24"           # Sub-range of the VPC’s IP range.
  availability_zone       = "ap-south-1a"            # Puts subnet in a specific AWS AZ.
  map_public_ip_on_launch = true                    # Automatically gives instances public IPs.

  tags = {
    # Example name: "niura-production-subnet-public"
    Name = "${var.project_name}-${var.environment}-subnet-public"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "ap-south-1b"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.environment}-subnet-public-b"
  }
}


########################################
# 🌍 INTERNET GATEWAY (IGW)
########################################

# This acts like your VPC’s “door” to the Internet.
# Without an Internet Gateway, nothing inside your VPC can reach the Internet.
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id   # Attaches to your main VPC.

  tags = {
    # Example: "niura-production-igw"
    Name = "${var.project_name}-${var.environment}-igw"
  }
}


########################################
# 🛣️ ROUTE TABLE (Public Routes)
########################################

# A route table defines *how* traffic moves inside your VPC.
# This one sends all outbound traffic (0.0.0.0/0) to the Internet Gateway.
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  # Create a route for Internet traffic
  route {
    cidr_block = "0.0.0.0/0"                # Means "all traffic"
    gateway_id = aws_internet_gateway.igw.id  # Send it out through the Internet Gateway
  }

  tags = {
    # Example: "niura-production-public-rt"
    Name = "${var.project_name}-${var.environment}-public-rt"
  }
}


########################################
# 🔗 ASSOCIATE ROUTE TABLE WITH SUBNET
########################################

# Connects the route table (above) with the subnet (above).
# This makes your subnet “public” — i.e., its instances can reach the Internet.
resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}


########################################
# 🧾 OUTPUTS (useful references for other modules or scripts)
########################################

# These outputs print after `terraform apply`
# and can be used by other Terraform modules or AWS resources.

output "vpc_id" {
  value = aws_vpc.main.id
}

output "subnet_ids" {
  value = [aws_subnet.public.id, aws_subnet.public_b.id]
}

output "route_table_id" {
  description = "Public route table ID for VPC endpoints"
  value       = aws_route_table.public_rt.id
}
