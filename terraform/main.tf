provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "cloudsocial_images" {
  bucket = "cloudsocial-images"
}

resource "aws_security_group" "cloudsocial_sg" {
  description = "Managed by Terraform"


  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }


  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }


  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "cloudsocial" {
  ami                    = "ami-00e801948462f718a"
  instance_type          = "t2.micro"
  subnet_id              = "subnet-0f198884b45b64996"
  vpc_security_group_ids = ["sg-03f7a83373480ae5c"]
  key_name               = "lekatraining-us-east-1"
  iam_instance_profile   = "instanceRole"


  tags = {
    Name = "Cloud-Monitoring-Control-Room"
  }
}
