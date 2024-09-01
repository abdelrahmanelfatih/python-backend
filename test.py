from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import threading

TELEGRAM_TOKEN = 'YOUR_BOT_TOKEN'  # Replace with your actual Telegram bot token

app = FastAPI()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Telegram Application globally
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

@app.post("/send")
async def receive_message(request: Request):
    try:
        data = await request.json()  # Get the JSON body of the request

        # Extract the fields from the incoming data
        items = data.get("items", [])
        total = data.get("total", "0.00")
        currency = data.get("currency", "USD")
        require_name = data.get("requireName", False)
        require_email = data.get("requireEmail", False)
        require_phone = data.get("requirePhone", False)
        protect_content = data.get("protectContent", False)
        chat_id = data.get("chatId")  # Extract the chat ID from the incoming data

        if not chat_id:
            raise ValueError("Chat ID is missing.")

        # Convert prices to the smallest unit of the given currency (e.g., cents for USD, pence for GBP)
        multiplier = 100  # Default multiplier for most currencies (like USD, EUR, GBP)

        # Adjust if a different currency with a different smallest unit factor is used
        if currency in ['USD', 'EUR', 'GBP']:
            multiplier = 100  # 1 unit = 100 cents/pence/etc.

        # Create labeled price list and calculate the correct total amount
        prices = [
            LabeledPrice(label=item['title'], amount=int(float(item['price']) * multiplier) * item['quantity'])
            for item in items
        ]

        # Calculate the correct total amount in the smallest currency unit
        total_amount = sum(price.amount for price in prices)

        # Validate that the calculated total matches the provided total
        if total_amount != int(float(total) * multiplier):
            raise ValueError("The total amount does not match the sum of item prices.")

        # Send invoice using the /sendInvoice command
        await telegram_app.bot.send_invoice(
            chat_id=chat_id,
            title="Invoice",
            description="Your purchase details",
            payload="custom-payload",
            provider_token="YOUR_PROVIDER_TOKEN",  # Replace with your payment provider token
            currency=currency,
            prices=prices,
            need_name=require_name,
            need_email=require_email,
            need_phone_number=require_phone,
            protect_content=protect_content,
            start_parameter="start_parameter"
        )

        return {"message": "Invoice sent successfully", "chat_id": chat_id}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Telegram bot command handler functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello there!')

async def run_bot():
    # Add command handlers
    telegram_app.add_handler(CommandHandler("start", start))

    # Start the bot
    await telegram_app.initialize()  # Initialize the bot
    await telegram_app.start()

    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        await telegram_app.stop()

async def main():
    # Run FastAPI server in a separate thread or process
    threading.Thread(target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8080}, daemon=True).start()

    # Run Telegram bot
    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())
