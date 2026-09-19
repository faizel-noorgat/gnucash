-- Initialize RLS infrastructure for multi-tenancy
-- This script sets up the PostgreSQL session variables and RLS policies

-- Create application role for RLS (separate from table owner)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user NOLOGIN;
    END IF;
END
$$;

-- Grant connect to application role
GRANT CONNECT ON DATABASE gnucash_dev TO app_user;

-- Create function to get current tenant ID from session
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS uuid AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Create function to get current user ID from session
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS integer AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_id', TRUE), '')::integer;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Create function to get current entity ID from session
CREATE OR REPLACE FUNCTION get_current_entity_id()
RETURNS integer AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_entity_id', TRUE), '')::integer;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Note: Individual RLS policies will be created by Django migrations
-- for each tenant-scoped table using the functions above.
-- Example policy template:
--
-- CREATE POLICY tenant_isolation ON identity_tenant
--     FOR ALL TO app_user
--     USING (id = get_current_tenant_id());
--
-- ALTER TABLE identity_tenant ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE identity_tenant FORCE ROW LEVEL SECURITY;
