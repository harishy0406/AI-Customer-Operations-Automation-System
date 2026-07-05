from src.eval.runner import EvalExample


DEFAULT_GOLDEN_SET: list[EvalExample] = [
    EvalExample(
        query="What is your return policy?",
        expected_answer="Our return policy allows returns within 30 days of purchase.",
        expected_sources=["returns_policy"],
    ),
    EvalExample(
        query="How do I reset my password?",
        expected_answer="You can reset your password by clicking 'Forgot Password' on the login page.",
        expected_sources=["account_help"],
    ),
    EvalExample(
        query="What are your business hours?",
        expected_answer="Our business hours are Monday to Friday, 9 AM to 6 PM EST.",
        expected_sources=["company_info"],
    ),
    EvalExample(
        query="Do you offer international shipping?",
        expected_answer="Yes, we ship to over 50 countries worldwide.",
        expected_sources=["shipping_policy"],
    ),
    EvalExample(
        query="How can I track my order?",
        expected_answer="You can track your order using the tracking link sent to your email.",
        expected_sources=["order_tracking"],
    ),
]
