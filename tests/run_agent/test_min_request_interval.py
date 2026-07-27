import time
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from run_agent import AIAgent

def test_min_request_interval_throttling():
    """Verify that min_request_interval causes the loop to sleep between rapid requests."""
    cfg = {
        "providers": {
            "nvidia": {
                "min_request_interval": 1.5
            }
        },
        "agent": {
            "api_max_retries": 3
        }
    }

    # Setup agent with mocked config and client
    with patch("run_agent.OpenAI") as mock_openai, \
         patch("hermes_cli.config.load_config", return_value=cfg), \
         patch("hermes_cli.config.load_config_readonly", return_value=cfg), \
         patch("time.sleep") as mock_sleep:
        
        # Mock the chat completions client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Create a clean mock response using SimpleNamespace
        mock_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        role="assistant",
                        content="Response content",
                        tool_calls=None,
                        function_call=None,
                        reasoning_content=None,
                        reasoning=None,
                    ),
                    finish_reason="stop"
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
        )
        mock_client.chat.completions.create.return_value = mock_response

        agent = AIAgent(
            api_key="test-key",
            provider="nvidia",
            base_url="https://integrate.api.nvidia.com/v1",
            model="moonshotai/kimi-k2.6",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )

        # Use a controllable time variable for time.monotonic
        current_time = 100.0
        def mock_monotonic():
            return current_time

        # First API call
        with patch("time.monotonic", side_effect=mock_monotonic):
            agent.run_conversation("Hello 1")
            
            # Reset sleep mock to count only subsequent sleeps
            mock_sleep.reset_mock()

            # Advance current time by 0.5s before the second request
            # Since min_request_interval is 1.5s, it must sleep the remaining 1.0s
            current_time = 100.5
            agent.run_conversation("Hello 2")

            # Verify sleep was called to satisfy the min request interval
            assert mock_sleep.called
            # The total sleep time should be around 1.0s (min_interval 1.5 - elapsed 0.5)
            sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
            total_sleep = sum(sleep_args)
            assert 0.9 <= total_sleep <= 1.1
