http://admin:admin@localhost:8081/db/trademan/trademan_clients/
http://admin:admin@localhost:8081/db/trademan/strategies

http://admin@trademan.com:admin@localhost:8082/
docker exec -it trademan_postgres psql -U admin -d trademan 
-c "SELECT * FROM financials LIMIT 5;"

This is my current CLI client menu example.

==================================================
           TradeMan V1 Script Executor            
==================================================
1. Morning Scripts
2. Evening Scripts
3. Strategy Scripts
4. Weekly Reports
5. Celery Scripts
6. Restart Scripts
7. Migration Scripts
8. API Testing Scripts
0. Exit
==================================================

Enter your choice (0-8): 1

==================================================
              1. Morning Scripts Menu               
==================================================
1. 0830_GoodMorning.sh
2. TelegramOrderBot.py
3. FundValidator.py
4. DailyLogin.py
5. MarketInfoUpdate.py
6. AsmGsmAggregator.py
7. DailyEquityCalc.py
8. DailyInstrumentAggregator.py
9. Chat Agent. 
10. Back to Main Menu
==================================================

1.9. Chat Agent. 
Desciption: Please help me implement a pydantic agents using https://ai.pydantic.dev/agents/ as reference. Implement one agent each of 8 TradeMan V1 Script Executor option as an extra option as shown in example for Morning Scripts above.

notes:
- Pydantic_ai Ethos: https://ai.pydantic.dev/
- run 'ollama run llama3.2' to start the ollama server
- Use '''
  from pydantic import BaseModel

from pydantic_ai import Agent


class CityLocation(BaseModel):
    city: str
    country: str


agent = Agent('ollama:llama3.2', result_type=CityLocation) '''

example to instantiate the agent using ollama. Fit the agent to our use case.

- Make the @Master.py script modular into 3 files to make easier to manage.
-  Keep agents modular and so that user can add more areas of expertise to the agent.
- Create an comprehensive {Area}Expert.md in Experts/ folder for each area of expertise from the above mentioned list. Provide common commands and their usage for each area of expertise.
- Provide Base class and detailed implementation of each area of expertise by having a separate file for each area of expertise 


