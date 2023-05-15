import telebot
from telebot import types
from inventory_items import inventory
from secret import TOKEN, SHOPKEEPERS_CHAT_ID
def main():
    # Create the bot and get the updater
    bot = telebot.TeleBot(TOKEN)
    cart = []
    
    # shopkeeper's chat id
    shopkeeper_chat_id = SHOPKEEPERS_CHAT_ID

    @bot.message_handler(commands=['start'])
    def start(message):
        instructions = '''
        Welcome to the General Store Bot! Here are the available commands:

        /browse - Browse the inventory and add items to your cart
        /cart - View your cart.
        /remove - To remove an item, use /remove followed by the item number.
        /checkout - Proceed to checkout.

        '''
        bot.send_message(message.chat.id, instructions)
    
    # Command handler for /browse
    @bot.message_handler(commands=['browse'])
    def browse(message):
        # Get unique sections from the inventory
        sections = list(set(item['section'] for item in inventory))

        # Display the sections as buttons
        markup = types.InlineKeyboardMarkup()
        for section in sections:
            button = types.InlineKeyboardButton(section, callback_data=f"section_{section}")
            markup.add(button)
        bot.send_message(message.chat.id, 'Please select a section:', reply_markup=markup)

    # Callback handler for section selection
    @bot.callback_query_handler(func=lambda call: call.data.startswith('section_'))
    def show_items(call):
        # Get the selected section
        selected_section = call.data.split('_')[1]

        # Get the items within the selected section
        items = [item for item in inventory if item['section'] == selected_section]

        if len(items) == 0:
            bot.send_message(call.message.chat.id, 'No items found in this section.')
        else:
            # Display the items as buttons
            markup = types.InlineKeyboardMarkup()
            for item in items:
                button = types.InlineKeyboardButton(f"{item['name']} (₹{item['price']:.2f})", callback_data=f"add_{item['name']}")
                markup.add(button)
            bot.send_message(call.message.chat.id, 'Please select an item to add to your cart:', reply_markup=markup)

    # Callback handler for item selection
    @bot.callback_query_handler(func=lambda call: call.data.startswith('add_'))
    def add_to_cart(call):
        # Get the selected item
        selected_item = next((item for item in inventory if item['name'] == call.data.split('_')[1]), None)

        # Add or update the item in the cart
        if selected_item:
            item_in_cart = next((item for item in cart if item['name'] == selected_item['name']), None)
            if item_in_cart:
                item_in_cart['quantity'] += 1
            else:
                cart.append({'name': selected_item['name'], 'price': selected_item['price'], 'quantity': 1})
            bot.answer_callback_query(call.id, f"You have added {selected_item['name']} to your cart.")

   
        # Command handler for /cart
    @bot.message_handler(commands=['cart'])
    def view_cart(message):
        if len(cart) == 0:
            bot.send_message(message.chat.id, 'Your cart is empty.')
        else:
            cart_message = 'Your cart contains the following items:\n\n'
            for index, item in enumerate(cart, start=1):
                item_name = item['name']
                item_price = item['price']
                item_quantity = item['quantity']
                cart_message += f"{index}. {item_name} (₹{item_price:.2f}) - Quantity: {item_quantity}\n"
            cart_message += '\nTo remove an item, use /remove followed by the item number.'
            bot.send_message(message.chat.id, cart_message)

    # Command handler for /remove
    @bot.message_handler(commands=['remove'])
    def remove_item(message):
        # Get the item number to remove
        command_args = message.text.split()
        if len(command_args) != 2:
            bot.send_message(message.chat.id, 'Invalid command. Please specify the item number to remove.')
            return

        try:
            item_number = int(command_args[1])
            if item_number < 1 or item_number > len(cart):
                bot.send_message(message.chat.id, 'Invalid item number. Please specify a valid item number.')
                return

            # Remove the item from the cart
            removed_item = cart[item_number - 1]
            if removed_item['quantity'] > 1:
                removed_item['quantity'] -= 1
            else:
                cart.pop(item_number - 1)
            bot.send_message(message.chat.id, f"You have removed {removed_item['name']} from your cart.")

        except ValueError:
            bot.send_message(message.chat.id, 'Invalid item number. Please specify a valid item number.')

    # Command handler for /checkout
    @bot.message_handler(commands=['checkout'])
    def checkout(message):
        if len(cart) == 0:
            bot.send_message(message.chat.id, 'Your cart is empty. Please add items to your cart before checking out.')
        else:
            total_cost = sum(item['price'] * item['quantity'] for item in cart)
            bot.send_message(message.chat.id, f'Your total cost is ₹{total_cost:.2f}. Please provide your contact details for delivery.')
            bot.send_message(message.chat.id, 'Please provide your name:')
            bot.register_next_step_handler(message, process_name)

    def process_name(message):
        name = message.text
        bot.send_message(message.chat.id, f'Thank you, {name}!\nPlease provide your phone number for delivery.')
        bot.register_next_step_handler(message, process_phone_number, name)

    def process_phone_number(message, name):
        phone_number = message.text

        if validate_phone_number(phone_number):
            order_details = 'Order Details:'
            for item in cart:
                item_name = item['name']
                item_price = item['price']
                item_quantity = item['quantity']
                order_details += f"\n- {item_name} (₹{item_price:.2f}) - Quantity: {item_quantity}"
            total_cost = sum(item['price'] * item['quantity'] for item in cart)

            order_details += f'\nTotal Cost: ₹{total_cost:.2f}'

            order_details += "\nPlease confirm your order by typing 'confirm' or cancel by typing 'cancel'."

            bot.send_message(message.chat.id, order_details)
            bot.register_next_step_handler(message, process_order_confirmation, total_cost, name, phone_number)

        else:
            bot.send_message(message.chat.id, "Invalid phone number. Please try again /checkout.")

    def process_order_confirmation(message, total_cost, name, phone_number):
        confirmation = message.text.lower()
        if confirmation == 'confirm':
            # Send the order details to the user and the shopkeeper
            user_message = f"Thank you, {name}! Your order has been confirmed.\n\n"
            user_message += "Order Details:\n"
            for item in cart:
                item_name = item['name']
                item_price = item['price']
                item_quantity = item['quantity']
                user_message += f"\n- {item_name} (₹{item_price:.2f}) - Quantity: {item_quantity}"
            total_cost = sum(item['price'] * item['quantity'] for item in cart)
            
            user_message += f'\nTotal Cost: ₹{total_cost:.2f}'


            # Send order details to shopkeeper
            shopkeeper_message = 'New Order Details:\n\n'
            for item in cart:
                item_name = item['name']
                item_price = item['price']
                item_quantity = item['quantity']
                shopkeeper_message += f"- {item_name} (₹{item_price:.2f}) - Quantity: {item_quantity}\n"
            shopkeeper_message += f'Total Cost: ₹{total_cost:.2f}\n'
            shopkeeper_message += f'Customer Name: {message.from_user.first_name}\n'
            shopkeeper_message += f'Phone Number: {phone_number}'

            bot.send_message(message.chat.id, user_message)
            bot.send_message(message.chat.id, 'Thank you for your order! The shopkeeper will contact you soon.')

            bot.send_message(shopkeeper_chat_id, shopkeeper_message)

            cart.clear()

        elif confirmation == 'cancel':
            bot.send_message(message.chat.id, 'Your order has been canceled. If you have any further questions, feel free to ask.')

        else:
            bot.send_message(message.chat.id, "Invalid input. Please type 'confirm' to confirm the order or 'cancel' to cancel the order.")

    def validate_phone_number(mobile_number):
        # Add your phone number validation logic here
        if not mobile_number.isdigit() or len(mobile_number) != 10:
            return False
        return True

    # Start the bot
    bot.polling()


if __name__ == "__main__":
    main()
