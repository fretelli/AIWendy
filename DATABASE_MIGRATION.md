# Database Migration Guide

## Running the Exchange Connections Migration

A new database table `exchange_connections` has been added to support user-level exchange API key management.

### Apply the Migration

#### Option 1: Using Docker (Recommended)

```bash
# The migration will run automatically when you restart the containers
docker-compose down
docker-compose up --build
```

#### Option 2: Manual Migration

```bash
cd aiwendy

# Run the migration
alembic upgrade head
```

### Verify Migration

Check that the new table was created:

```sql
-- Connect to your PostgreSQL database
psql postgresql://keeltrader:password@localhost:5432/keeltrader

-- List all tables
\dt

-- You should see: exchange_connections

-- Check the table structure
\d exchange_connections
```

### Migration Details

**File:** `aiwendy/migrations/versions/010_create_exchange_connections.py`

**Changes:**
- Creates `exchangetype` ENUM type
- Creates `exchange_connections` table with encrypted credential storage
- Adds foreign key to `users.id`
- Creates indexes for performance

**Table Structure:**
```sql
CREATE TABLE exchange_connections (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    exchange_type exchangetype NOT NULL,
    name VARCHAR(100),
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    passphrase_encrypted TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_testnet BOOLEAN NOT NULL DEFAULT false,
    last_sync_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Rollback (if needed)

To rollback this migration:

```bash
cd aiwendy
alembic downgrade -1
```

This will:
- Drop the `exchange_connections` table
- Drop the `exchangetype` ENUM type

### Troubleshooting

#### Migration Already Applied

If you see an error like "relation already exists":

```bash
# Check current migration version
alembic current

# Should show: 010 (head)

# If not, force to head
alembic stamp head
```

#### Permission Denied

If you get permission errors:

```bash
# Make sure your database user has CREATE permissions
GRANT CREATE ON SCHEMA public TO keeltrader;
```

#### Enum Type Conflict

If the ENUM type already exists:

```sql
-- Drop it manually first
DROP TYPE IF EXISTS exchangetype CASCADE;

-- Then rerun the migration
```

## Next Steps

After applying the migration:

1. ✅ Restart your API server
2. ✅ Test the new endpoints: `/api/v1/user/exchanges`
3. ✅ Build the frontend settings page for users to add their exchange connections

---

For more information, see [MARKET_DATA_INTEGRATION.md](./MARKET_DATA_INTEGRATION.md)
