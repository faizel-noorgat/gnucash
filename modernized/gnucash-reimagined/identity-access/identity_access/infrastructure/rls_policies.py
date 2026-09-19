"""
Row Level Security (RLS) Policies

SQL migration helpers for creating and managing RLS policies.
"""


class RLSPolicyManager:
    """
    Manager for creating and managing PostgreSQL RLS policies.

    Key points:
    - All tenant-scoped tables must have FORCE ROW LEVEL SECURITY
    - Policies check session variables for tenant/user context
    - Policies fail closed (no access if context not set)
    """

    @staticmethod
    def enable_rls_on_table(table_name):
        """
        Generate SQL to enable RLS on a table.

        Args:
            table_name: Name of the table

        Returns:
            SQL string
        """
        return f"""
        ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;
        """

    @staticmethod
    def create_tenant_isolation_policy(table_name, tenant_column='tenant_id'):
        """
        Generate SQL to create tenant isolation policy.

        Args:
            table_name: Name of the table
            tenant_column: Name of the tenant_id column

        Returns:
            SQL string
        """
        return f"""
        CREATE POLICY tenant_isolation_policy ON {table_name}
        USING (
            {tenant_column}::text = current_setting('app.current_tenant_id', true)
        );
        """

    @staticmethod
    def create_practice_access_policy(table_name, tenant_column='tenant_id'):
        """
        Generate SQL to create practice access policy.

        This allows practice users to access client tenant data
        when they have an active advisor access grant.

        Args:
            table_name: Name of the table
            tenant_column: Name of the tenant_id column

        Returns:
            SQL string
        """
        return f"""
        CREATE POLICY practice_access_policy ON {table_name}
        USING (
            EXISTS (
                SELECT 1 FROM advisor_access_grants aag
                JOIN client_engagements ce ON aag.engagement_id = ce.guid
                WHERE ce.tenant_id = {table_name}.{tenant_column}
                AND aag.practice_user_id::text = current_setting('app.current_user_id', true)
                AND ce.status = 'active'
                AND aag.revoked_at IS NULL
                AND (aag.expires_at IS NULL OR aag.expires_at > NOW())
            )
        );
        """

    @staticmethod
    def create_entity_scoped_policy(table_name, entity_column='legal_entity_id'):
        """
        Generate SQL to create entity-scoped access policy.

        Args:
            table_name: Name of the table
            entity_column: Name of the entity_id column

        Returns:
            SQL string
        """
        return f"""
        CREATE POLICY entity_scoped_policy ON {table_name}
        USING (
            {entity_column}::text = current_setting('app.current_entity_id', true)
            OR current_setting('app.current_entity_id', true) IS NULL
        );
        """

    @staticmethod
    def create_audit_policy(table_name):
        """
        Generate SQL to create audit policy (no updates/deletes).

        Args:
            table_name: Name of the table

        Returns:
            SQL string
        """
        return f"""
        CREATE POLICY audit_policy ON {table_name}
        FOR SELECT
        USING (true);

        CREATE POLICY audit_no_update ON {table_name}
        FOR UPDATE
        USING (false);

        CREATE POLICY audit_no_delete ON {table_name}
        FOR DELETE
        USING (false);
        """

    @staticmethod
    def generate_rls_migration(app_label, model_name, tenant_column='tenant_id'):
        """
        Generate complete RLS migration for a model.

        Args:
            app_label: Django app label
            model_name: Model name
            tenant_column: Name of the tenant_id column

        Returns:
            SQL string
        """
        table_name = f'{app_label}_{model_name.lower()}'

        return f"""
        -- Enable RLS on {table_name}
        {RLSPolicyManager.enable_rls_on_table(table_name)}

        -- Create tenant isolation policy
        {RLSPolicyManager.create_tenant_isolation_policy(table_name, tenant_column)}

        -- Create practice access policy
        {RLSPolicyManager.create_practice_access_policy(table_name, tenant_column)}
        """
