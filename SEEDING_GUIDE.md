# Production Database Seeding Guide

## Overview
The NEMS backend now includes automatic database seeding that works in production environments. This ensures your database is populated with admin users and sample products automatically when deployed.

## How It Works

### Automatic Seeding on Startup
The system automatically seeds data when:
1. **Production Environment**: Detects production deployment (Render, Railway, etc.)
2. **Empty Database**: No users or products exist in the database
3. **Manual Trigger**: Environment variable `SEED_DATABASE=true`

### Seeding Process
1. **Database Initialization**: Creates all necessary tables
2. **Admin Users**: Creates 5 admin users with credentials
3. **Sample Products**: Adds 3 sample products with images
4. **JSON Import**: Imports from `seed_products.json` if available

## Admin Users Created
```
1. Username: admin     Password: admin123
2. Username: super     Password: super123
3. Username: manager   Password: manager456
4. Username: director  Password: director789
5. Username: root      Password: root2024
```

## Sample Products Created
1. **Bannière Déroulante Premium** (ROLL-UP)
2. **X-Banner Professionnel** (X-BANNER)
3. **Bannière Volante télescopique** (FLYING BANNER)

## Environment Variables

### Production Seeding Control
```bash
# Force seeding (even if data exists)
SEED_DATABASE=true

# Production detection (automatic)
RENDER=true
RAILWAY_ENVIRONMENT=production
ENVIRONMENT=production
```

### Database Configuration
```bash
# Required for database connection
DATABASE_URL=postgresql://user:pass@host:port/dbname

# JWT settings
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Deployment Scenarios

### 1. Fresh Production Deployment
- **What happens**: Database is empty, auto-seeding triggers
- **Result**: Admin users + sample products created
- **Logs**: Shows seeding process and credentials

### 2. Existing Production Database
- **What happens**: Users/products detected, seeding skipped
- **Result**: No changes to existing data
- **Logs**: Shows "Database already contains data"

### 3. Manual Reseeding
- **What happens**: Set `SEED_DATABASE=true` to force reseeding
- **Result**: Fresh data seeded (overwrites duplicates)
- **Logs**: Shows reseeding process

## Render Deployment Setup

### Environment Variables in Render
```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Authentication
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: Force seeding
SEED_DATABASE=true

# CORS
ALLOWED_ORIGINS=https://your-frontend.onrender.com
```

### Deployment Process
1. **Deploy Backend**: Create Render Web Service
2. **Database Setup**: PostgreSQL database created
3. **Auto-Seeding**: On first startup, seeds automatically
4. **Check Logs**: Verify seeding completed successfully

## Manual Seeding Commands

### Run Seeding Manually
```bash
# From backend directory
python -m app.seed

# Or directly
python app/seed.py
```

### Force Reseeding
```bash
# Set environment variable and restart
export SEED_DATABASE=true
python main.py
```

## Seeding File Structure

### Core Seeding Module
```
backend/app/seed.py
```

### Sample Data Files
```
backend/seed_products.json  # Optional: Custom product data
```

### Integration Points
```
backend/main.py             # Startup event integration
backend/app/database.py    # Database initialization
```

## Monitoring Seeding

### Log Messages to Watch For
```
=== NEMS Database Seeding Started ===
Seeding admin users...
  + Created admin user: admin
  + Created admin user: super
Seeding sample products...
  + Created sample product: Bannière Déroulante Premium
=== Database Seeding Completed Successfully! ===
```

### Error Messages
```
Error during database seeding: [error details]
Database already contains data, skipping seeding
```

## Troubleshooting

### Common Issues

#### 1. Seeding Not Triggering
**Problem**: Database not seeding in production
**Solution**: Check environment variables
```bash
# Verify production detection
echo $RENDER
echo $RAILWAY_ENVIRONMENT

# Force seeding
export SEED_DATABASE=true
```

#### 2. Database Connection Errors
**Problem**: Can't connect to database during seeding
**Solution**: Verify DATABASE_URL format
```bash
# Test connection
python -c "from app.database import engine; print(engine.execute('SELECT 1').scalar())"
```

#### 3. Permission Errors
**Problem**: Can't create users/products
**Solution**: Check database permissions
```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE your_db TO your_user;
```

#### 4. Duplicate Data
**Problem**: Seeding creates duplicates
**Solution**: System prevents duplicates by checking existing data

### Debug Commands
```bash
# Check database contents
python -c "
from app.database import SessionLocal
from app.models.user import User
from app.models.product import Product
db = SessionLocal()
print(f'Users: {db.query(User).count()}')
print(f'Products: {db.query(Product).count()}')
db.close()
"

# Test seeding logic
python -c "
from app.seed import should_seed_database, is_production_environment
print(f'Production: {is_production_environment()}')
print(f'Should seed: {should_seed_database()}')
"
```

## Best Practices

### Production Deployment
1. **Test Locally**: Verify seeding works before deployment
2. **Check Logs**: Monitor seeding process on first deploy
3. **Backup Data**: Before manual reseeding
4. **Environment Variables**: Use proper secrets management

### Data Management
1. **Custom Products**: Add to `seed_products.json` for custom data
2. **Admin Credentials**: Change passwords after first deployment
3. **Sample Data**: Remove or modify sample products as needed
4. **Version Control**: Don't commit sensitive data

## Security Considerations

### Admin Passwords
- Default passwords are for initial setup only
- Change passwords after first login
- Use strong passwords in production

### Database Access
- Limit database user permissions
- Use connection pooling
- Monitor for suspicious activity

### Environment Variables
- Never commit secrets to git
- Use Render's environment variable management
- Rotate secrets regularly

## Support

If seeding fails:
1. Check Render logs for error messages
2. Verify database connection
3. Test seeding locally first
4. Check environment variables
5. Ensure database permissions are correct

Your NEMS system will now automatically set up admin users and sample products in production!
