http://admin:admin@localhost:8081/db/trademan/trademan_clients/
http://admin:admin@localhost:8081/db/trademan/strategies

http://admin@trademan.com:admin@localhost:8082/
docker exec -it trademan_postgres psql -U admin -d trademan 
-c "SELECT * FROM financials LIMIT 5;"


Plan of action:
1. 