import os
import csv
from openai import OpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import difflib

# Initialize OpenAI client
# client = OpenAI(api_key="Your OpenAI Key")

# Define the state schema
class State(TypedDict):
    text: Optional[str]
    national_id: Optional[str]
    action: Optional[str]
    llm_response: Optional[str]
    status: Optional[str]
    result: Optional[str]
    error: Optional[str]
    customer_id: Optional[str]

# CSV load utility
def load_csv_column(path, key):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row[key].strip() for row in reader if row.get(key)]

# Load customer map: national_id -> customer_id
def load_customer_map(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {
            row["national_id"].strip(): row["customer_id"].strip()
            for row in reader
            if row.get("national_id") and row.get("customer_id")
        }

# Load action map: action_name -> description
def load_action_map(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {
            row["action_name"].strip().lower(): row["description"].strip()
            for row in reader if row.get("action_name") and row.get("description")
        }
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
customer_csv_path = os.path.join(BASE_DIR, "customer.csv")
actions_csv_path = os.path.join(BASE_DIR, "actions.csv")

customer_map = load_customer_map(customer_csv_path)
action_map = load_action_map(actions_csv_path)
#Load CSVs
# customer_map = load_customer_map("agent/customer.csv")
# action_map = load_action_map("agent/actions.csv")

# Node: Extract info from text using GPT (clean and direct)
def extract_fields_from_text(state: State) -> State:
    extraction_prompt = f"""
You are reading a court order document.

Extract the following fields:
- National ID
- Action (such as:
    "Freeze all associated bank accounts",
    "All funds linked to their bank accounts are to be immediately released",
    "Individual's bank accounts be immediately frozen to prevent unauthorized transactions",
    "Any assets or accounts associated with said individual are to be immediately suspended until further notice",
    "Transfer of all available funds initiated to a designated external account"
)

Court Order:
{state['text']}

Respond strictly in this format:
National ID: <value>
Action: <value>
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0,
        )
        answer = response.choices[0].message.content.strip()
        state["llm_response"] = answer

        for line in answer.splitlines():
            if line.lower().startswith("national id"):
                state["national_id"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("action"):
                state["action"] = line.split(":", 1)[1].strip()

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"LLM extraction failed: {e}"

    return state


CUSTOMER_CSV_PATH = os.path.join(os.path.dirname(__file__), "customer.csv")

# Load customer.csv only once at the start
def load_customer_map():
    customer_map = {}
    with open(CUSTOMER_CSV_PATH, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            customer_map[row['national_id'].strip()] = row['customer_id'].strip()
    return customer_map

customer_map = load_customer_map()

def validate_customer(state: State) -> State:
    national_id = state.get("national_id", "").strip()
    print(f"[DEBUG] National ID from state: '{national_id}'")

    print(f"[DEBUG] Keys in customer_map: {list(customer_map.keys())}")

    if national_id in customer_map:
        state["customer_id"] = customer_map[national_id]
        print(f"[DEBUG] Match found: Customer ID = {state['customer_id']}")
    else:
        state["status"] = "discarded"
        state["error"] = f"Person with National ID {national_id} is not a customer"
        print(f"[DEBUG] No match found. Order discarded.")

    return state

# Node: Validate action
def validate_action(state: State) -> State:
    extracted_action = state.get("action", "").lower().strip()
    print(f"\n Extracted action (input): '{extracted_action}'")

    best_match = None
    best_score = 0.0

    print(" Matching against known actions:")
    for action_key, description in action_map.items():
        score = difflib.SequenceMatcher(None, extracted_action, description.lower()).ratio()
        print(f"  - Comparing with '{description}' → Score: {score:.4f}")
        if score > best_score:
            best_score = score
            best_match = action_key

    print(f"\n Best Match: '{best_match}' with Score: {best_score:.4f}")

    if best_score > 0.6:  # Adjust threshold if needed
        print(f" Match accepted. Updating action to '{best_match}'")
        state["action"] = best_match
    else:
        print(f" No acceptable match found. Marking action as invalid.")
        state["status"] = "discardaction"
        state["error"] = f"Action '{extracted_action}' is not recognized or allowed"

    return state

#  Node: Execute the action (simulate)
def execute_action(state: State) -> State:
    state["status"] = "executed"
    state["result"] = f"Action '{state.get('action')}' executed for Customer ID: {state.get('customer_id')}"
    return state

#  Build the LangGraph
workflow = StateGraph(State)

workflow.add_node("extract_fields", extract_fields_from_text)
workflow.add_node("validate_customer", validate_customer)
workflow.add_node("validate_action", validate_action)
workflow.add_node("execute_action", execute_action)

workflow.set_entry_point("extract_fields")
workflow.add_edge("extract_fields", "validate_customer")

workflow.add_conditional_edges(
    "validate_customer",
    lambda state: "validate_action" if state.get("status") is None else END,
    {
        "validate_action": "validate_action",
        END: END
    }
)

workflow.add_conditional_edges(
    "validate_action",
    lambda state: "execute_action" if state.get("status") is None else END,
    {
        "execute_action": "execute_action",
        END: END
    }
)

workflow.add_edge("execute_action", END)

#  Compile app
app = workflow.compile()

# FastAPI calls this
def process_court_order(text: str) -> State:
    state = {"text": text}
    return app.invoke(state)
