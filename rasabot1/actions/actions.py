from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


class ActionProvideTickets(Action):

    def name(self) -> Text:
        return "action_provide_tickets"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Fetching slot values
        ticket_type = tracker.get_slot("ticket_type")
        adult_count = tracker.get_slot("adult_count")
        children_count = tracker.get_slot("children_count")

        # Handling cases where slots might not be set
        if not ticket_type or not adult_count or not children_count:
            dispatcher.utter_message(text="Sorry, I don't have enough information to process your booking.")
            return []

        # Sending a message with the ticket details
        dispatcher.utter_message(
            text=f"Here are your {adult_count} adult and {children_count} children tickets for {ticket_type}. Thank you!"
        )
        return []

class ActionRespondWithIntent(Action):
    def name(self) -> Text:
        return "action_respond_with_intent"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Get the reply_type from custom metadata or set to 'unknown' if not present
        reply_type = tracker.latest_message.get('custom', {}).get('reply_type', 'unknown')

        # Print out the reply_type for debugging purposes
        print(f"Bot's Reply Type: {reply_type}")

        # Send the reply message to the user
        dispatcher.utter_message(text=f"The bot's current reply type is: {reply_type}")

        # Return empty list or further actions if needed
        return []

class ActionResetSlots(Action):
    def name(self) -> str:
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        return [
            SlotSet("adult_count", None),
            SlotSet("children_count", None),
            SlotSet("nationality", None),
            SlotSet("ticket_type", None),
        ]