from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord import ButtonStyle, Interaction

from src.database.models import Ban, MinorReport
from src.views.minorreportview import MinorReportView
from tests import helpers


class TestMinorReportView:
    """Test the MinorReportView Discord UI component."""

    @pytest.mark.asyncio
    async def test_approve_ban_button_success(self, bot):
        """Test approving a ban successfully."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Reviewer")
        interaction.guild = helpers.MockGuild()
        interaction.message = helpers.MockMessage(id=12345)
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.edit_original_response = AsyncMock()

        # Mock the report
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=2,
            suspected_age=15,
            evidence="Evidence",
            report_message_id=12345,
            status="pending"
        )

        # Mock user to ban
        mock_user = helpers.MockMember(id=999, name="Minor User")

        with (
            patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock,
            patch('src.views.minorreportview.AsyncSessionLocal') as session_mock,
            patch('src.views.minorreportview.ban_member', new_callable=AsyncMock) as ban_mock
        ):
            # Mock authorization
            auth_mock.return_value = True

            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_report

            # Mock ban_member
            ban_mock.return_value = MagicMock(message="User banned")

            # Mock bot.get_member_or_user
            interaction.client = bot
            bot.get_member_or_user.return_value = mock_user

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.approve_ban.callback(interaction)

            # Assertions
            auth_mock.assert_called_once_with(interaction.user.id)
            ban_mock.assert_called_once()
            interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_ban_button_unauthorized(self, bot):
        """Test approve ban button with unauthorized user."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Unauthorized User")
        interaction.response.send_message = AsyncMock()

        with patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock:
            # Mock not authorized
            auth_mock.return_value = False

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.approve_ban.callback(interaction)

            # Assertions
            auth_mock.assert_called_once_with(interaction.user.id)
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args
            assert "not authorized" in str(call_args).lower() or "permission" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_approve_ban_button_report_not_found(self, bot):
        """Test approve ban button when report is not found."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Reviewer")
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        with (
            patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock,
            patch('src.views.minorreportview.AsyncSessionLocal') as session_mock
        ):
            # Mock authorization
            auth_mock.return_value = True

            # Mock session with no report found
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.approve_ban.callback(interaction)

            # Assertions
            interaction.followup.send.assert_called()
            call_args = interaction.followup.send.call_args
            assert "not found" in str(call_args).lower() or "error" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_check_consent_button_success_with_consent(self, bot):
        """Test check consent button when consent is found."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Reviewer")
        interaction.guild = helpers.MockGuild()
        interaction.message = helpers.MockMessage(id=12345)
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.edit_original_response = AsyncMock()

        # Mock the report with associated ban
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=2,
            suspected_age=15,
            evidence="Evidence",
            report_message_id=12345,
            status="approved",
            associated_ban_id=5
        )

        # Mock the ban
        mock_ban = Ban(
            id=5,
            user_id=999,
            moderator_id=2,
            reason="Underage",
            unban_time=1234567890
        )

        # Mock user
        mock_user = helpers.MockMember(id=999, name="Minor User")

        with (
            patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock,
            patch('src.views.minorreportview.AsyncSessionLocal') as session_mock,
            patch('src.views.minorreportview.check_parental_consent', new_callable=AsyncMock) as consent_mock,
            patch('src.views.minorreportview.unban_member', new_callable=AsyncMock) as unban_mock,
            patch('src.views.minorreportview.calculate_age_from_dob') as age_mock
        ):
            # Mock authorization
            auth_mock.return_value = True

            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.side_effect = lambda model, id: mock_report if model == MinorReport else mock_ban

            # Mock consent found
            consent_mock.return_value = {
                "consent": True,
                "dob": "2008-05-15"
            }

            # Mock age calculation
            age_mock.return_value = 15

            # Mock bot.get_member_or_user
            interaction.client = bot
            bot.get_member_or_user.return_value = mock_user

            # Mock unban
            unban_mock.return_value = mock_user

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.check_consent.callback(interaction)

            # Assertions
            auth_mock.assert_called_once_with(interaction.user.id)
            consent_mock.assert_called_once()
            unban_mock.assert_called_once()
            interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_consent_button_no_consent_found(self, bot):
        """Test check consent button when no consent is found."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Reviewer")
        interaction.message = helpers.MockMessage(id=12345)
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Mock the report
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=2,
            suspected_age=15,
            evidence="Evidence",
            report_message_id=12345,
            status="approved"
        )

        with (
            patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock,
            patch('src.views.minorreportview.AsyncSessionLocal') as session_mock,
            patch('src.views.minorreportview.check_parental_consent', new_callable=AsyncMock) as consent_mock
        ):
            # Mock authorization
            auth_mock.return_value = True

            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_report

            # Mock no consent found
            consent_mock.return_value = {"consent": False}

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.check_consent.callback(interaction)

            # Assertions
            auth_mock.assert_called_once_with(interaction.user.id)
            consent_mock.assert_called_once()
            interaction.followup.send.assert_called()
            call_args = interaction.followup.send.call_args
            assert "not found" in str(call_args).lower() or "no consent" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_deny_report_button_success(self, bot):
        """Test denying a report successfully."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Reviewer")
        interaction.message = helpers.MockMessage(id=12345)
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.edit_original_response = AsyncMock()

        # Mock the report
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=2,
            suspected_age=15,
            evidence="Evidence",
            report_message_id=12345,
            status="pending"
        )

        with (
            patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock,
            patch('src.views.minorreportview.AsyncSessionLocal') as session_mock
        ):
            # Mock authorization
            auth_mock.return_value = True

            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_report

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.deny_report.callback(interaction)

            # Assertions
            auth_mock.assert_called_once_with(interaction.user.id)
            interaction.response.defer.assert_called_once()
            assert mock_report.status == "denied"

    @pytest.mark.asyncio
    async def test_view_button_styles(self, bot):
        """Test that view buttons have correct styles."""
        view = MinorReportView(bot, 1)

        # Check button styles
        assert view.approve_ban.style == ButtonStyle.danger
        assert view.check_consent.style == ButtonStyle.success
        assert view.deny_report.style == ButtonStyle.secondary

    @pytest.mark.asyncio
    async def test_view_button_labels(self, bot):
        """Test that view buttons have correct labels."""
        view = MinorReportView(bot, 1)

        # Check button labels
        assert "Approve" in view.approve_ban.label or "Ban" in view.approve_ban.label
        assert "Check" in view.check_consent.label or "Consent" in view.check_consent.label
        assert "Deny" in view.deny_report.label or "False" in view.deny_report.label

    @pytest.mark.asyncio
    async def test_check_consent_user_now_adult(self, bot):
        """Test check consent when user is now 18+ (should not assign minor role)."""
        # Create mock interaction
        interaction = AsyncMock(spec=Interaction)
        interaction.user = helpers.MockMember(id=1, name="Reviewer")
        interaction.guild = helpers.MockGuild()
        interaction.message = helpers.MockMessage(id=12345)
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.edit_original_response = AsyncMock()

        # Mock the report with associated ban
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=2,
            suspected_age=15,
            evidence="Evidence",
            report_message_id=12345,
            status="approved",
            associated_ban_id=5
        )

        # Mock the ban
        mock_ban = Ban(
            id=5,
            user_id=999,
            moderator_id=2,
            reason="Underage",
            unban_time=1234567890
        )

        # Mock user
        mock_user = helpers.MockMember(id=999, name="Now Adult User")

        with (
            patch('src.views.minorreportview.is_authorized_reviewer', new_callable=AsyncMock) as auth_mock,
            patch('src.views.minorreportview.AsyncSessionLocal') as session_mock,
            patch('src.views.minorreportview.check_parental_consent', new_callable=AsyncMock) as consent_mock,
            patch('src.views.minorreportview.unban_member', new_callable=AsyncMock) as unban_mock,
            patch('src.views.minorreportview.calculate_age_from_dob') as age_mock
        ):
            # Mock authorization
            auth_mock.return_value = True

            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.side_effect = lambda model, id: mock_report if model == MinorReport else mock_ban

            # Mock consent found
            consent_mock.return_value = {
                "consent": True,
                "dob": "2000-01-01"  # DOB makes them 18+ now
            }

            # Mock age calculation - now 18+
            age_mock.return_value = 24

            # Mock bot.get_member_or_user
            interaction.client = bot
            bot.get_member_or_user.return_value = mock_user

            # Mock unban
            unban_mock.return_value = mock_user

            # Create view and call the button callback
            view = MinorReportView(bot, 1)
            await view.check_consent.callback(interaction)

            # Assertions
            auth_mock.assert_called_once_with(interaction.user.id)
            consent_mock.assert_called_once()
            unban_mock.assert_called_once()
            # Should NOT add minor role since they're now 18+
            mock_user.add_roles.assert_not_called()
