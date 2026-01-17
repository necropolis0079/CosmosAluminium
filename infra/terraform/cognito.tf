# =============================================================================
# LCMGoCloud-CAGenAI - Cognito User Pool & Authentication
# =============================================================================
# User Groups:
#   - SuperAdmin: Full system access, user management
#   - Admins: HR managers, CV management, reports
#   - HRUsers: HR staff, CV upload, basic queries
# =============================================================================

# -----------------------------------------------------------------------------
# Cognito User Pool
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-users"

  # Username configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Password policy
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # MFA configuration (optional, can be enabled per user)
  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  # User attribute schema
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 5
      max_length = 256
    }
  }

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                     = "department"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 0
      max_length = 100
    }
  }

  # Email configuration (using Cognito default)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Admin create user config
  admin_create_user_config {
    allow_admin_create_user_only = true # Only admins can create users

    invite_message_template {
      email_subject = "Welcome to LCMGoCloud CA GenAI"
      email_message = "Your username is {username} and temporary password is {####}. Please login and change your password."
      sms_message   = "Your username is {username} and temporary password is {####}"
    }
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  # Verification message
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "LCMGoCloud CA GenAI - Verify your email"
    email_message        = "Your verification code is {####}"
  }

  # Device tracking
  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }

  tags = {
    Name = "${local.name_prefix}-users"
  }
}

# -----------------------------------------------------------------------------
# Cognito User Pool Domain
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name_prefix}-auth"
  user_pool_id = aws_cognito_user_pool.main.id
}

# -----------------------------------------------------------------------------
# Cognito User Pool Client (Web Application)
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name_prefix}-web-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # Token validity
  access_token_validity  = 1  # 1 hour
  id_token_validity      = 1  # 1 hour
  refresh_token_validity = 30 # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # OAuth configuration
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]

  # Callback URLs (update with actual domain)
  callback_urls = [
    "http://localhost:3000/callback",
    "https://${local.name_prefix}.amplifyapp.com/callback"
  ]

  logout_urls = [
    "http://localhost:3000/logout",
    "https://${local.name_prefix}.amplifyapp.com/logout"
  ]

  # Security settings
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true

  # Auth flows
  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Read/write attributes
  read_attributes = [
    "email",
    "name",
    "custom:department"
  ]

  write_attributes = [
    "email",
    "name",
    "custom:department"
  ]
}

# -----------------------------------------------------------------------------
# Cognito User Pool Client (API/Lambda - for backend auth)
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_client" "api" {
  name         = "${local.name_prefix}-api-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # No secret for Lambda use
  generate_secret = false

  # Token validity
  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 7

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Auth flows for API
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Security
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
}

# -----------------------------------------------------------------------------
# Cognito User Groups
# -----------------------------------------------------------------------------

# SuperAdmin Group - Full system access
resource "aws_cognito_user_group" "super_admin" {
  name         = "SuperAdmin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "System administrators with full access"
  precedence   = 1 # Highest priority
}

# Admins Group - HR managers
resource "aws_cognito_user_group" "admins" {
  name         = "Admins"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "HR managers with CV management and reporting access"
  precedence   = 10
}

# HRUsers Group - HR staff
resource "aws_cognito_user_group" "hr_users" {
  name         = "HRUsers"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "HR staff with CV upload and basic query access"
  precedence   = 100
}

# -----------------------------------------------------------------------------
# Resource Server (for API scopes)
# -----------------------------------------------------------------------------

resource "aws_cognito_resource_server" "api" {
  identifier   = "api"
  name         = "${local.name_prefix}-api"
  user_pool_id = aws_cognito_user_pool.main.id

  scope {
    scope_name        = "cv.read"
    scope_description = "Read CV data"
  }

  scope {
    scope_name        = "cv.write"
    scope_description = "Upload and modify CVs"
  }

  scope {
    scope_name        = "query.execute"
    scope_description = "Execute queries"
  }

  scope {
    scope_name        = "admin.users"
    scope_description = "Manage users"
  }

  scope {
    scope_name        = "admin.system"
    scope_description = "System administration"
  }
}
