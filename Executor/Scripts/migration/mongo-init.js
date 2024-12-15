// Create trademan database
db = db.getSiblingDB('trademan');

// Create user for the trademan database
db.createUser({
    user: 'admin',
    pwd: 'admin',
    roles: [
        {
            role: 'readWrite',
            db: 'trademan'
        }
    ]
});

// Create collections with indexes
db.createCollection('clients');
db.clients.createIndex({ "Tr_No": 1 }, { unique: true });

db.createCollection('strategies');
db.strategies.createIndex({ "StrategyName": 1 }, { unique: true });

db.createCollection('admin');
