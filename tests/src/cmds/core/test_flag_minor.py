from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cmds.core import flag_minor
from src.database.models import MinorReport, MinorReviewReviewer
from tests import helpers


class TestFlagMinorCog:
    """Test the `FlagMinor` cog."""

    @pytest.mark.asyncio
    async def test_flag_minor_success_no_htb_account(self, ctx, bot):
        """Test flagging a minor with no HTB account linked."""
        ctx.user = helpers.MockMember(id=1, name="Test Moderator")
        user = helpers.MockMember(id=2, name="Suspected Minor")
        bot.get_member_or_user.return_value = user

        with (
            patch('src.cmds.core.flag_minor.get_htb_discord_link', new_callable=AsyncMock) as get_link_mock,
            patch('src.cmds.core.flag_minor.check_parental_consent', new_callable=AsyncMock) as consent_mock,
            patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock
        ):
            # Mock no HTB account linked
            get_link_mock.return_value = None

            # Mock session for database operations
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # No existing report

            # Mock message sent to review channel
            mock_message = helpers.MockMessage(id=12345)
            ctx.bot.get_channel.return_value.send = AsyncMock(return_value=mock_message)

            cog = flag_minor.FlagMinorCog(bot)
            await cog.flag_minor.callback(
                cog, ctx, user, 15, "User stated they are 15 in chat"
            )

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            get_link_mock.assert_called_once_with(user.id)
            # Should not check consent if no HTB account
            consent_mock.assert_not_called()
            # Should have responded with report created message
            assert ctx.followup.send.called

    @pytest.mark.asyncio
    async def test_flag_minor_success_htb_account_no_consent(self, ctx, bot):
        """Test flagging a minor with HTB account but no parental consent."""
        ctx.user = helpers.MockMember(id=1, name="Test Moderator")
        user = helpers.MockMember(id=2, name="Suspected Minor")
        bot.get_member_or_user.return_value = user

        mock_htb_link = type('obj', (object,), {
            'htb_id': 123,
            'user_id': 2
        })()

        with (
            patch('src.cmds.core.flag_minor.get_htb_discord_link', new_callable=AsyncMock) as get_link_mock,
            patch('src.cmds.core.flag_minor.check_parental_consent', new_callable=AsyncMock) as consent_mock,
            patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock
        ):
            # Mock HTB account linked
            get_link_mock.return_value = mock_htb_link

            # Mock no consent found
            consent_mock.return_value = {"consent": False}

            # Mock session for database operations
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # No existing report

            # Mock message sent to review channel
            mock_message = helpers.MockMessage(id=12345)
            ctx.bot.get_channel.return_value.send = AsyncMock(return_value=mock_message)

            cog = flag_minor.FlagMinorCog(bot)
            await cog.flag_minor.callback(
                cog, ctx, user, 15, "User stated they are 15 in chat"
            )

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            get_link_mock.assert_called_once_with(user.id)
            consent_mock.assert_called_once()
            # Should have responded with report created message
            assert ctx.followup.send.called

    @pytest.mark.asyncio
    async def test_flag_minor_consent_already_exists(self, ctx, bot):
        """Test flagging a minor when parental consent already exists."""
        ctx.user = helpers.MockMember(id=1, name="Test Moderator")
        user = helpers.MockMember(id=2, name="Suspected Minor")
        bot.get_member_or_user.return_value = user

        mock_htb_link = type('obj', (object,), {
            'htb_id': 123,
            'user_id': 2
        })()

        with (
            patch('src.cmds.core.flag_minor.get_htb_discord_link', new_callable=AsyncMock) as get_link_mock,
            patch('src.cmds.core.flag_minor.check_parental_consent', new_callable=AsyncMock) as consent_mock,
            patch('src.cmds.core.flag_minor.calculate_age_from_dob') as age_mock
        ):
            # Mock HTB account linked
            get_link_mock.return_value = mock_htb_link

            # Mock consent found
            consent_mock.return_value = {
                "consent": True,
                "dob": "2008-05-15"
            }

            # Mock age as 15 (still a minor)
            age_mock.return_value = 15

            cog = flag_minor.FlagMinorCog(bot)
            await cog.flag_minor.callback(
                cog, ctx, user, 15, "User stated they are 15 in chat"
            )

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            get_link_mock.assert_called_once_with(user.id)
            consent_mock.assert_called_once()
            # Should have responded that consent already exists
            assert ctx.followup.send.called
            # Check the message contains information about consent
            call_args = ctx.followup.send.call_args
            assert "parental consent" in str(call_args).lower() or "verified" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_flag_minor_existing_report(self, ctx, bot):
        """Test flagging a minor when a report already exists."""
        ctx.user = helpers.MockMember(id=1, name="Test Moderator")
        user = helpers.MockMember(id=2, name="Suspected Minor")
        bot.get_member_or_user.return_value = user

        existing_report = MinorReport(
            id=1,
            user_id=2,
            reporter_id=3,
            suspected_age=15,
            evidence="Previous evidence",
            report_message_id=99999,
            status="pending"
        )

        with (
            patch('src.cmds.core.flag_minor.get_htb_discord_link', new_callable=AsyncMock) as get_link_mock,
            patch('src.cmds.core.flag_minor.check_parental_consent', new_callable=AsyncMock) as consent_mock,
            patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock
        ):
            # Mock no HTB account
            get_link_mock.return_value = None

            # Mock session with existing report
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session

            # Mock the select query to return existing report
            mock_result = type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'first': lambda: existing_report
                })()
            })()
            mock_session.execute.return_value = mock_result

            cog = flag_minor.FlagMinorCog(bot)
            await cog.flag_minor.callback(
                cog, ctx, user, 15, "User stated they are 15 in chat"
            )

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            # Should have responded that report already exists
            assert ctx.followup.send.called
            call_args = ctx.followup.send.call_args
            assert "already" in str(call_args).lower() or "existing" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_flag_minor_invalid_age(self, ctx, bot):
        """Test flagging with an invalid age (outside 1-17 range)."""
        ctx.user = helpers.MockMember(id=1, name="Test Moderator")
        user = helpers.MockMember(id=2, name="User")
        bot.get_member_or_user.return_value = user

        cog = flag_minor.FlagMinorCog(bot)

        # Test age too low
        await cog.flag_minor.callback(
            cog, ctx, user, 0, "Evidence"
        )
        ctx.response.defer.assert_called_with(ephemeral=True)

        # Test age too high
        ctx.reset_mock()
        await cog.flag_minor.callback(
            cog, ctx, user, 18, "Evidence"
        )
        ctx.response.defer.assert_called_with(ephemeral=True)

    @pytest.mark.asyncio
    async def test_minor_reviewers_add_success(self, ctx, bot):
        """Test adding a reviewer successfully."""
        ctx.user = helpers.MockMember(id=1, name="Admin")
        reviewer = helpers.MockMember(id=2, name="New Reviewer")

        with (
            patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock,
            patch('src.cmds.core.flag_minor.invalidate_reviewer_cache') as invalidate_mock
        ):
            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session

            # Mock no existing reviewer
            mock_result = type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'first': lambda: None
                })()
            })()
            mock_session.execute.return_value = mock_result

            cog = flag_minor.FlagMinorCog(bot)
            await cog.minor_reviewers_add.callback(cog, ctx, reviewer)

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            invalidate_mock.assert_called_once()
            assert ctx.followup.send.called
            call_args = ctx.followup.send.call_args
            assert "added" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_minor_reviewers_add_already_exists(self, ctx, bot):
        """Test adding a reviewer that already exists."""
        ctx.user = helpers.MockMember(id=1, name="Admin")
        reviewer = helpers.MockMember(id=2, name="Existing Reviewer")

        existing_reviewer = MinorReviewReviewer(
            id=1,
            user_id=2,
            added_by=3
        )

        with (
            patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock,
        ):
            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session

            # Mock existing reviewer
            mock_result = type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'first': lambda: existing_reviewer
                })()
            })()
            mock_session.execute.return_value = mock_result

            cog = flag_minor.FlagMinorCog(bot)
            await cog.minor_reviewers_add.callback(cog, ctx, reviewer)

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            assert ctx.followup.send.called
            call_args = ctx.followup.send.call_args
            assert "already" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_minor_reviewers_remove_success(self, ctx, bot):
        """Test removing a reviewer successfully."""
        ctx.user = helpers.MockMember(id=1, name="Admin")
        reviewer = helpers.MockMember(id=2, name="Reviewer to Remove")

        existing_reviewer = MinorReviewReviewer(
            id=1,
            user_id=2,
            added_by=3
        )

        with (
            patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock,
            patch('src.cmds.core.flag_minor.invalidate_reviewer_cache') as invalidate_mock
        ):
            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session

            # Mock existing reviewer
            mock_result = type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'first': lambda: existing_reviewer
                })()
            })()
            mock_session.execute.return_value = mock_result

            cog = flag_minor.FlagMinorCog(bot)
            await cog.minor_reviewers_remove.callback(cog, ctx, reviewer)

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            invalidate_mock.assert_called_once()
            assert ctx.followup.send.called
            call_args = ctx.followup.send.call_args
            assert "removed" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_minor_reviewers_list_success(self, ctx, bot):
        """Test listing reviewers successfully."""
        ctx.user = helpers.MockMember(id=1, name="Admin")

        mock_reviewers = [
            MinorReviewReviewer(id=1, user_id=111, added_by=1),
            MinorReviewReviewer(id=2, user_id=222, added_by=1),
            MinorReviewReviewer(id=3, user_id=333, added_by=1),
        ]

        with patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock:
            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session

            # Mock reviewer list
            mock_result = type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'all': lambda: mock_reviewers
                })()
            })()
            mock_session.execute.return_value = mock_result

            # Mock bot.get_user to return mock users
            bot.get_user = lambda user_id: helpers.MockUser(id=user_id, name=f"User{user_id}")

            cog = flag_minor.FlagMinorCog(bot)
            await cog.minor_reviewers_list.callback(cog, ctx)

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            assert ctx.followup.send.called
            call_args = ctx.followup.send.call_args
            # Should list all 3 reviewers
            assert "111" in str(call_args) or "User111" in str(call_args)

    @pytest.mark.asyncio
    async def test_minor_reviewers_list_empty(self, ctx, bot):
        """Test listing reviewers when list is empty."""
        ctx.user = helpers.MockMember(id=1, name="Admin")

        with patch('src.cmds.core.flag_minor.AsyncSessionLocal') as session_mock:
            # Mock session
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session

            # Mock empty reviewer list
            mock_result = type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'all': lambda: []
                })()
            })()
            mock_session.execute.return_value = mock_result

            cog = flag_minor.FlagMinorCog(bot)
            await cog.minor_reviewers_list.callback(cog, ctx)

            # Assertions
            ctx.response.defer.assert_called_once_with(ephemeral=True)
            assert ctx.followup.send.called
            call_args = ctx.followup.send.call_args
            assert "no" in str(call_args).lower() or "empty" in str(call_args).lower()

    def test_setup(self, bot):
        """Test the setup method of the cog."""
        # Invoke the command
        flag_minor.setup(bot)

        bot.add_cog.assert_called_once()
