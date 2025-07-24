import os
import csv
from openai import OpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import difflib

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

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
    dummy:Optional[str]

# CSV loading utilities
def load_customer_map(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {
            row["national_id"].strip(): row["customer_id"].strip()
            for row in reader
            if row.get("national_id") and row.get("customer_id")
        }

def load_action_map(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {
            row["action_name"].strip().lower(): row["description"].strip()
            for row in reader if row.get("action_name") and row.get("description")
        }

# Load CSVs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
customer_csv_path = os.path.join(BASE_DIR, "customer.csv")
actions_csv_path = os.path.join(BASE_DIR, "actions.csv")

customer_map = load_customer_map(customer_csv_path)
action_map = load_action_map(actions_csv_path)

# Node: Extract fields from court order using LLM
def extract_fields_from_text(state: State) -> State:
    prompt = f"""
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
            messages=[{"role": "user", "content": prompt}],
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

# Node: Validate customer from national ID
def validate_customer(state: State) -> State:
    national_id = state.get("national_id", "").strip()
    if national_id in customer_map:
        state["customer_id"] = customer_map[national_id]
    else:
        state["status"] = "discarded"
        state["error"] = f"Person with National ID {national_id} is not a customer"
    return state

# Node: Validate and match action
def validate_action(state: State) -> State:
    extracted_action = state.get("action", "").lower().strip()

    best_match = None
    best_score = 0.0

    for action_key, description in action_map.items():
        score = difflib.SequenceMatcher(None, extracted_action, description.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = action_key

    if best_score > 0.6:
        state["action"] = best_match
    else:
        state["status"] = "discardaction"
        state["error"] = f"Action '{extracted_action}' is not recognized or allowed"

    return state

# Node: Simulate execution
def execute_action(state: State) -> State:
    state["status"] = "executed"
    state["result"] = f"Action '{state.get('action')}' executed for Customer ID: {state.get('customer_id')}"
    return state

# Node: Dummy action simulation
def perform_dummy_action(state: State) -> State:
    action = state.get("action")
    customer_id = state.get("customer_id")

    if not action or not customer_id:
        state["status"] = "error"
        state["error"] = "Missing action or customer_id for dummy execution"
        return state

    if action == "freeze_funds_pass":
        result = f"[Dummy] Funds frozen for customer {customer_id}"
    elif action == "release_funds_pass":
        result = f"[Dummy] Funds released for customer {customer_id}"
    else:
        result = f"[Dummy] Unknown action '{action}' for customer {customer_id}"

    state["dummy"] = "dummy_executed"
    return state  #  return the (possibly unchanged) state

# LangGraph: Build the graph
workflow = StateGraph(State)

workflow.add_node("extract_fields", extract_fields_from_text)
workflow.add_node("validate_customer", validate_customer)
workflow.add_node("validate_action", validate_action)
workflow.add_node("execute_action", execute_action)
workflow.add_node("perform_dummy_action", perform_dummy_action)

workflow.set_entry_point("extract_fields")
workflow.add_edge("extract_fields", "validate_customer")

workflow.add_conditional_edges(
    "validate_customer",
    lambda state: "validate_action" if state.get("status") is None else END,
    {
        "validate_action": "validate_action",
        END: END,
    }
)

workflow.add_conditional_edges(
    "validate_action",
    lambda state: "execute_action" if state.get("status") is None else END,
    {
        "execute_action": "execute_action",
        END: END,
    }
)

workflow.add_edge("execute_action", "perform_dummy_action")
workflow.add_edge("perform_dummy_action", END)

# Compile the graph
app = workflow.compile()

# Public function to invoke
def process_court_order(text: str) -> State:
    return app.invoke({"text": text})
