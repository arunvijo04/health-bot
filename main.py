from fetch_product_details import fetch_product_by_barcode
from config import ALLERGEN_MAP
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

user_state = {}

def format_product_info(product):
    """Format product details into a neatly aligned string for WhatsApp display."""
    product_name = product.get('product_name', 'N/A')
    brand        = product.get('brands', 'N/A')
    ingredients  = product.get('ingredients_text', 'N/A').replace('\n', ' ')  # Keeping ingredients in one line
    categories   = product.get('categories', 'N/A')
    nova_group   = product.get('nova_group', 'N/A')
    energy       = product.get('nutriments', {}).get('energy-kcal_100g', 'N/A')
    sugar        = product.get('nutriments', {}).get('sugars_100g', 'N/A')
    fat          = product.get('nutriments', {}).get('fat_100g', 'N/A')
    sodium       = product.get('nutriments', {}).get('salt_100g', 'N/A')

    return (f"-- Product Information --\n"
            f"Product Name      :    {product_name}\n"
            f"Brand             :    {brand}\n"
            f"Ingredients       :    {ingredients}\n"
            f"Categories        :    {categories}\n"
            f"NOVA Group        :    {nova_group}\n"
            f"Energy            :    {energy} kcal\n"
            f"Sugar             :    {sugar} g\n"
            f"Fat               :    {fat} g\n"
            f"Sodium            :    {sodium} g\n")


def check_allergy(allergies, product):
    """Check if the product contains any allergens."""
    ingredients = product.get('ingredients_text', '').lower()
    for allergy in allergies:
        if allergy.lower() in ingredients:
            return f"--- Allergy Alert ---\nThis product is NOT suitable for you!\nAllergens Found:\n- {allergy}\nIngredients: {product.get('ingredients_text', 'N/A')}"
    return "This product is suitable for you based on your allergy profile."

def health_analysis(product, diabetes):
    """Analyze product for harmful ingredients and provide a health score."""
    sugar = product.get('nutriments', {}).get('sugars_100g', 'N/A')
    harmful_ingredients = []
    score = 10

    if diabetes == 'yes' and sugar != 'N/A' and float(sugar) > 5:
        harmful_ingredients.append('High sugar content')
        score -= 8

    if harmful_ingredients:
        return (f"--- Health Analysis ---\nHarmful Ingredients: {', '.join(harmful_ingredients)}\nSuitability Score: {score}/10\nReasons: {', '.join(harmful_ingredients)}")
    else:
        return "--- Health Analysis ---\nHarmful Ingredients: None\nSuitability Score: 10/10\nThis product is safe based on your profile."

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    """Respond to incoming WhatsApp messages."""
    global user_state
    incoming_msg = request.values.get('Body', '').strip().lower()
    response = MessagingResponse()
    sender = request.values.get('From', '')

    if sender not in user_state:
        user_state[sender] = {'step': 'welcome'}

    step = user_state[sender]['step']

    if step == 'welcome':
        reply = "Hello! Welcome to the Food Health Analysis Tool. Please type 'Start' to begin."
        user_state[sender]['step'] = 'started'

    elif step == 'started' and incoming_msg == 'start':
        reply = "Do you have diabetes? Please reply with 'Yes' or 'No'."
        user_state[sender]['step'] = 'diabetes_check'

    elif step == 'diabetes_check':
        if incoming_msg in ['yes', 'no']:
            user_state[sender]['diabetes'] = incoming_msg
            reply = "Do you have any allergies? Please reply with 'Yes' or 'No'."
            user_state[sender]['step'] = 'allergy_check'
        else:
            reply = "Please reply with 'Yes' or 'No' regarding diabetes."

    elif step == 'allergy_check':
        if incoming_msg == 'yes':
            reply = "Please specify your allergies (e.g., 'peanut, gluten')."
            user_state[sender]['step'] = 'allergy_type'
        elif incoming_msg == 'no':
            user_state[sender]['allergies'] = []
            reply = "--- Main Menu ---\n1. Search product by barcode\n2. Check for misleading claims by barcode\n3. Exit\nChoose an option (1-3):"
            user_state[sender]['step'] = 'main_menu'
        else:
            reply = "Please reply with 'Yes' or 'No' regarding allergies."

    elif step == 'allergy_type':
        user_state[sender]['allergies'] = incoming_msg.split(', ')
        reply = "--- Main Menu ---\n1. Search product by barcode\n2. Check for misleading claims by barcode\n3. Exit\nChoose an option (1-3):"
        user_state[sender]['step'] = 'main_menu'

    elif step == 'main_menu':
        if incoming_msg == '1':
            reply = "Enter the product barcode:"
            user_state[sender]['step'] = 'barcode_request'
        elif incoming_msg == '2':
            reply = "Enter the product barcode to check for misleading claims:"
            user_state[sender]['step'] = 'claim_check'
        elif incoming_msg == '3':
            reply = "Thank you for using the Food Health Analysis Tool! Have a great day! 👋"
            user_state.pop(sender)
        else:
            reply = "Please choose a valid option (1-3)."

    elif step == 'barcode_request':
        barcode = incoming_msg
        product = fetch_product_by_barcode(barcode)

        if product:
            product_info = format_product_info(product)
            allergy_alert = check_allergy(user_state[sender].get('allergies', []), product)
            health_info = health_analysis(product, user_state[sender]['diabetes'])

            reply = f"{product_info}\n\n{allergy_alert}\n\n{health_info}\n\n--- Main Menu ---\n1. Search product by barcode\n2. Check for misleading claims by barcode\n3. Exit\nChoose an option (1-3):"
            user_state[sender]['step'] = 'main_menu'
        else:
            reply = "Product not found. Please try a different barcode."

    elif step == 'claim_check':
        reply = "Enter the claim to analyze (e.g., height growth, strength increase):"
        user_state[sender]['step'] = 'claim_analysis'

    elif step == 'claim_analysis':
        claim = incoming_msg
        # Assuming the claim analysis function is implemented elsewhere
        analysis_result = {
            "verdict": "Misleading",
            "why": ["Presence of artificial flavors and colors contradicts the 'natural' claim."]
        }
        reply = f"Claim Analysis Result:\n{analysis_result}"

        reply += "\n\n--- Main Menu ---\n1. Search product by barcode\n2. Check for misleading claims by barcode\n3. Exit\nChoose an option (1-3):"
        user_state[sender]['step'] = 'main_menu'

    else:
        reply = "Sorry, I didn't understand that. Please type 'Start' to begin."

    response.message(reply)
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)