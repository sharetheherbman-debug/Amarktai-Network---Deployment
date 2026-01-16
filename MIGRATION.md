# Database Migration Guide

## API Keys User ID Type Migration

### Overview
This migration converts the `user_id` field in the `api_keys` collection from MongoDB ObjectId to String format for consistency across the application.

### Why This Is Needed
- **Consistency**: JWT tokens store user_id as strings
- **Compatibility**: Ensures API key lookups work reliably
- **Future-proofing**: Simplifies authentication flow

### Pre-Migration Checklist
- [ ] Backup your MongoDB database
- [ ] Set environment variables: `MONGO_URL` and `DB_NAME`
- [ ] Test on a staging/development environment first
- [ ] Note: This migration is **idempotent** (safe to run multiple times)

### Running the Migration

#### Option 1: Automated Script (Recommended)
```bash
cd backend
python migrations/migrate_api_keys_user_id.py
```

The script will:
1. Connect to your MongoDB instance
2. Count documents that need migration
3. Ask for confirmation
4. Convert ObjectId user_id fields to strings
5. Add migration metadata to each document
6. Display a summary report

#### Option 2: Manual MongoDB Commands
If you prefer to run the migration manually using MongoDB shell:

```javascript
// Connect to your database
use amarktai_trading

// Find documents with ObjectId user_id
db.api_keys.find({ "user_id": { $type: "objectId" } }).forEach(function(doc) {
    db.api_keys.updateOne(
        { _id: doc._id },
        {
            $set: {
                user_id: doc.user_id.toString(),
                migrated_at: new Date().toISOString(),
                migration_note: "Converted from ObjectId to String"
            }
        }
    );
    print("Migrated: " + doc.provider + " for user " + doc.user_id.toString());
});

// Verify migration
print("Documents with ObjectId user_id remaining: " + 
    db.api_keys.countDocuments({ "user_id": { $type: "objectId" } }));
```

### Post-Migration Verification

1. **Check Migration Status**:
```bash
# All user_id fields should now be strings
mongo amarktai_trading --eval 'db.api_keys.find({ "user_id": { $type: "objectId" } }).count()'
# Should return: 0
```

2. **Test API Key Retrieval**:
```bash
# Test that API keys can be retrieved properly
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/api-keys
```

3. **Test Key Save/Update**:
- Go to dashboard Settings → API Keys
- Try saving a new API key
- Verify it saves with user_id as string

### Rollback (If Needed)
If you need to rollback (not recommended, but possible):

```javascript
// Only if you have the original ObjectId values stored in migration_note
db.api_keys.find({ "migration_note": { $exists: true } }).forEach(function(doc) {
    // Extract ObjectId from migration_note
    var match = doc.migration_note.match(/ObjectId\(([a-f0-9]+)\)/i);
    if (match) {
        db.api_keys.updateOne(
            { _id: doc._id },
            {
                $set: { user_id: ObjectId(match[1]) },
                $unset: { migrated_at: "", migration_note: "" }
            }
        );
    }
});
```

### Backward Compatibility
The application code includes backward compatibility:
- `get_decrypted_key()` function tries both string and ObjectId lookups
- New API key saves always use string user_id
- Existing code continues to work during migration period

### Timeline
- **Development/Staging**: Run migration immediately
- **Production**: Schedule during low-traffic window
- **Duration**: ~1 second per 1000 documents (typically < 5 seconds total)

### Support
If you encounter issues:
1. Check MongoDB logs: `docker logs amarktai-mongo`
2. Check application logs: `docker logs amarktai-backend`
3. Verify environment variables are set correctly
4. Ensure MongoDB connection is stable

### Related Changes
This migration is part of the following improvements:
- ✅ User ID type consistency everywhere
- ✅ API key payload compatibility (apiKey/api_key variants)
- ✅ Wallet manager using encrypted keys properly
- ✅ Test status tracking (Saved & Tested ✅)
- ✅ System status endpoint for monitoring

### Testing After Migration
1. **Save a new API key**: Should work normally
2. **List API keys**: Should show all existing keys
3. **Test an API key**: Should validate against exchange
4. **Delete an API key**: Should remove properly
5. **Fetch wallet balance**: Should work with Luno/other exchanges
6. **Overview dashboard**: Should display live balances

---

**Last Updated**: 2026-01-16  
**Migration Version**: 1.0  
**Status**: Required for production deployment
