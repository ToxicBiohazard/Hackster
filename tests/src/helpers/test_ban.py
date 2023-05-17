from unittest import mock
from unittest.mock import MagicMock, AsyncMock

import pytest
from discord import Forbidden, HTTPException

from src.helpers.ban import ban_member, _check_member, _dm_banned_member
from src.helpers.responses import SimpleResponse
from tests import helpers


class TestBanHelpers:

    @pytest.mark.asyncio
    async def test__check_member_staff_member(self, bot, guild, member):
        author = helpers.MockMember(name="Author User")
        member_is_staff = mock.Mock(return_value=True)
        with mock.patch('src.helpers.ban.member_is_staff', member_is_staff):
            response = await _check_member(bot, guild, member, author)
            assert isinstance(response, SimpleResponse)
            assert response.message == "You cannot ban another staff member."
            assert response.delete_after is None

    @pytest.mark.asyncio
    async def test__check_member_regular_member(self, bot, guild, member):
        author = helpers.MockMember(name="Author User")
        member_is_staff = mock.Mock(return_value=False)
        with mock.patch('src.helpers.ban.member_is_staff', member_is_staff):
            response = await _check_member(bot, guild, member, author)
            assert response is None

    @pytest.mark.asyncio
    async def test__check_member_user(self, bot, guild, user):
        author = helpers.MockMember(name="Author User")
        bot.get_member_or_user = AsyncMock()
        bot.get_member_or_user.return_value = user
        response = await _check_member(bot, guild, user, author)
        assert await bot.get_member_or_user.called_once_with(guild, user.id)
        assert response is None

    @pytest.mark.asyncio
    async def test__check_member_ban_bot(self, bot, guild, member):
        author = helpers.MockMember(name="Author User")
        member.bot = True
        response = await _check_member(bot, guild, member, author)
        assert isinstance(response, SimpleResponse)
        assert response.message == "You cannot ban a bot."
        assert response.delete_after is None

    @pytest.mark.asyncio
    async def test__check_member_ban_self(self, bot, guild, member):
        author = member
        response = await _check_member(bot, guild, member, author)
        assert isinstance(response, SimpleResponse)
        assert response.message == "You cannot ban yourself."
        assert response.delete_after is None

    @pytest.mark.asyncio
    async def test__dm_banned_member_success(self, guild, member):
        member.send = AsyncMock()
        end_date = "2023-05-19"
        reason = "Violation of community guidelines"
        result = await _dm_banned_member(end_date, guild, member, reason)
        member.send.assert_awaited_once_with(
            f"You have been banned from {guild.name} until {end_date} (UTC). "
            f"To appeal the ban, please reach out to an Administrator.\n"
            f"Following is the reason given:\n>>> {reason}\n"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test__dm_banned_member_forbidden_exception(self, guild, member):
        class MockResponse:
            def __init__(self, status, reason):
                self.status = status
                self.reason = reason

        response = MockResponse(403, "Forbidden")
        message = {
            "code": 403,
            "message": "Forbidden",
        }

        forbidden = Forbidden(response, message)
        member.send = AsyncMock(side_effect=forbidden)
        with pytest.warns(None):
            result = await _dm_banned_member("2023-05-19", guild, member, "Violation of community guidelines")
        assert result is False

    @pytest.mark.asyncio
    async def test__dm_banned_member_http_exception(self, guild, member):
        class MockResponse:
            def __init__(self, status, reason):
                self.status = status
                self.reason = reason

        response = MockResponse(500, "Internal Server Error")
        message = {
            "code": 500,
            "message": "Internal Server Error",
        }

        http_exception = HTTPException(response, message)
        member.send = AsyncMock(side_effect=http_exception)
        with pytest.warns(None):
            result = await _dm_banned_member("2023-05-19", guild, member, "Violation of community guidelines")
        assert result is False


class TestBanMember:

    @pytest.mark.asyncio
    async def test_ban_member_valid_duration(self, bot, guild, member, author):
        duration = "1d"
        reason = "xf reason"
        member.display_name = "Banned Member"

        with (
            mock.patch("src.helpers.ban._check_member", return_value=None),
            mock.patch("src.helpers.ban._dm_banned_member", return_value=True),
            mock.patch("src.helpers.ban._get_ban_or_create", return_value=(1, False)),
            mock.patch("src.helpers.ban.validate_duration", return_value=(1684276900, "")),
        ):
            mock_channel = helpers.MockTextChannel()
            mock_channel.send.return_value = MagicMock()
            guild.get_channel.return_value = mock_channel

            result = await ban_member(bot, guild, member, duration, reason)
            assert isinstance(result, SimpleResponse)
            assert result.message == f"{member.display_name} ({member.id}) has been banned until 2023-05-16 22:41:40 " \
                                     f"(UTC)."
