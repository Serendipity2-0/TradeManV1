import openai
import time
import yfinance as yf
import os, sys
from dotenv import load_dotenv
from SweepOrders import sweep_hedge_orders, sweep_sl_order


DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def sweep_orders():
    """
    This function logs the start of the order sweeping process, executes the hedge and stop-loss
    order sweeping functions, and returns a result message indicating the completion of the process.

    :return: A string indicating the completion of the order sweeping process.
    """
    logger.info("Sweeping orders for all active users in TradeMan system")

    sweep_hedge_orders()
    sweep_sl_order()
    result = "Sweeping orders completed"
    return result


tools_list = [
    {
        "type": "function",
        "function": {
            "name": "sweep_orders",
            "description": "Sweep the SL and Hedge orders for all active users in TradeMan system",
        },
    }
]


# Initialize the client
client = openai.OpenAI(
    api_key="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)

# Step 1: Create an Assistant
assistant = client.beta.assistants.create(
    name="Data Analyst Assistant",
    instructions="You are a personal Data Analyst Assistant",
    tools=tools_list,
    model="gpt-4-0125-preview",
)

# Step 2: Create a Thread
thread = client.beta.threads.create()

# Step 3: Add a Message to a Thread
message = client.beta.threads.messages.create(
    thread_id=thread.id, role="user", content="Can you sweep order for TradeMan?"
)

# Step 4: Run the Assistant
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
    instructions="You are order asssitant who will called to perform various operation on TradeMan trading system.",
)

print(run.model_dump_json(indent=4))

while True:
    # Wait for 5 seconds
    time.sleep(5)

    # Retrieve the run status
    run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    print(run_status.model_dump_json(indent=4))

    # If run is completed, get messages
    if run_status.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        # Loop through messages and print content based on role
        for msg in messages.data:
            role = msg.role
            content = msg.content[0].text.value
            print(f"{role.capitalize()}: {content}")

        break
    elif run_status.status == "requires_action":
        print("Function Calling")
        required_actions = run_status.required_action.submit_tool_outputs.model_dump()
        print(required_actions)
        tool_outputs = []
        import json

        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])

            if func_name == "sweep_orders":
                output = sweep_orders()
                tool_outputs.append({"tool_call_id": action["id"], "output": output})
            else:
                raise ValueError(f"Unknown function: {func_name}")

        print("Submitting outputs back to the Assistant...")
        client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
        )
    else:
        print("Waiting for the Assistant to process...")
        time.sleep(5)
