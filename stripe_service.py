import stripe
from dotenv import load_dotenv
import os

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


async def create_checkout_session(user_email: str, tier: str = "pro"):
    """Create a Stripe Checkout session for a subscription.

    Replace the price IDs below with your real Stripe Price IDs
    after creating products in the Stripe dashboard.
    """
    price_id = "price_1Q..." if tier == "pro" else "price_1..."

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="http://localhost:8501/?success=true",
        cancel_url="http://localhost:8501/?canceled=true",
        customer_email=user_email,
        metadata={"tier": tier},
    )
    return session.url
