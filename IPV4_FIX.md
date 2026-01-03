# Fix IPv4 Compatibility Issue

## 🔍 Problem Identified

The Supabase dashboard shows:
- **"Not IPv4 compatible"** warning
- Direct connection (port 5432) requires IPv6
- Your network is IPv4-only

## ✅ Solution: Use Session Pooler

The Session Pooler connection works with IPv4 networks.

## 📋 Steps to Get Pooler Connection String

### Step 1: In Supabase Dashboard

1. You're already on the **Settings → Database** page
2. Look for **"Connection string"** section
3. You should see tabs: **URI**, **JDBC**, **Golang**, etc.
4. Look for **"Session mode"** or **"Pooler"** tab/option

### Step 2: Get Pooler Connection String

The pooler connection string should look like:

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

OR for Session mode:

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?pgbouncer=true
```

**Key differences:**
- Uses `pooler.supabase.com` instead of `db.xxx.supabase.co`
- Port is `6543` (transaction mode) or `5432` with `pgbouncer=true` (session mode)
- Username includes project ref: `postgres.btzzflqfqitkjrmtfojg`

### Step 3: Click "Pooler settings" Button

1. Click the **"Pooler settings"** button you see in the dashboard
2. This should show you the pooler connection strings
3. Look for **"Session mode"** connection string
4. Copy it

### Step 4: Convert to AsyncPG Format

Once you have the pooler connection string:

**Original:**
```
postgresql://postgres.btzzflqfqitkjrmtfojg:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**For .env (add +asyncpg):**
```
postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:ItsTime%40365LetsGo@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Important:**
- Add `+asyncpg` after `postgresql`
- Encode password: `@` → `%40`
- Use the exact hostname from Supabase

## 🧪 Expected Pooler Connection String Format

Based on your project, it should be something like:

```
postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:ItsTime%40365LetsGo@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

OR (Session mode):

```
postgresql+asyncpg://postgres.btzzflqfqitkjrmtfojg:ItsTime%40365LetsGo@aws-0-us-east-1.pooler.supabase.com:5432/postgres?pgbouncer=true
```

## 📝 Quick Action

1. **Click "Pooler settings"** in Supabase dashboard
2. **Copy the Session mode connection string**
3. **Share it here** (or convert it yourself)
4. I'll update `.env` and test the connection

## ✅ After Update

Once we update to pooler connection, the connection should work immediately!


