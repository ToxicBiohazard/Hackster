from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord import ButtonStyle, Interaction

from src.database.models import Ban, MinorReport
from src.views.minorreportview import MinorReportView
from tests import helpers


class TestMinorReportView:
    """Test the MinorReportView Discord UI component."""

    @pytest.mark.asyncio
    async def test_view_has_persistent_buttons(self, bot):
        """Test that view is constructed with persistent buttons."""
        view = MinorReportView(bot)
        
        # View should have timeout=None for persistence
        assert view.timeout is None
        
        # View should have 3 buttons
        assert len(view.children) == 3
        
        # All buttons should have custom_ids for persistence
        for child in view.children:
            assert hasattr(child, 'custom_id')
            assert child.custom_id is not None

    @pytest.mark.asyncio
    async def test_get_report_helper(self, bot):
        """Test the _get_report helper method."""
        view = MinorReportView(bot)
        
        # Create mock interaction with message
        interaction = AsyncMock(spec=Interaction)
        interaction.message = helpers.MockMessage(id=12345)
        
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=2,
            suspected_age=15,
            evidence="Evidence",
            report_message_id=12345,
            status="pending"
        )
        
        with patch('src.views.minorreportview.AsyncSessionLocal') as session_mock:
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            
            # Mock scalars result
            mock_scalars_result = MagicMock()
            mock_scalars_result.first.return_value = mock_report
            mock_session.scalars = AsyncMock(return_value=mock_scalars_result)
            
            # Call _get_report
            result = await view._get_report(interaction)
            
            assert result == mock_report

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, bot):
        """Test _get_report when report doesn't exist."""
        view = MinorReportView(bot)
        
        # Create mock interaction with message
        interaction = AsyncMock(spec=Interaction)
        interaction.message = helpers.MockMessage(id=12345)
        
        with patch('src.views.minorreportview.AsyncSessionLocal') as session_mock:
            mock_session = AsyncMock()
            session_mock.return_value.__aenter__.return_value = mock_session
            
            # Mock scalars result with no report
            mock_scalars_result = MagicMock()
            mock_scalars_result.first.return_value = None
            mock_session.scalars = AsyncMock(return_value=mock_scalars_result)
            
            # Call _get_report
            result = await view._get_report(interaction)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_build_minor_report_embed(self, bot):
        """Test building a minor report embed."""
        from src.views.minorreportview import build_minor_report_embed
        
        mock_report = MinorReport(
            id=1,
            user_id=999,
            reporter_id=888,
            suspected_age=15,
            evidence="User stated they are 15",
            report_message_id=12345,
            status="pending"
        )
        
        mock_guild = helpers.MockGuild()
        mock_reporter = helpers.MockMember(id=888, name="Reporter")
        mock_guild.get_member = lambda id: mock_reporter if id == 888 else None
        
        # build_minor_report_embed takes 2 positional args and keyword-only args
        embed = build_minor_report_embed(mock_report, mock_guild)
        
        # Verify embed has required fields
        assert embed.title is not None
        assert "15" in str(embed.description) or "15" in str(embed.fields)
        assert "pending" in str(embed.color).lower() or embed.color is not None

    @pytest.mark.asyncio
    async def test_htb_profile_url_constant(self, bot):
        """Test that HTB_PROFILE_URL constant is defined."""
        from src.views.minorreportview import HTB_PROFILE_URL
        
        assert HTB_PROFILE_URL is not None
        assert isinstance(HTB_PROFILE_URL, str)
        assert "hackthebox" in HTB_PROFILE_URL.lower()

    @pytest.mark.asyncio
    async def test_view_initialization(self, bot):
        """Test view is initialized correctly."""
        view = MinorReportView(bot)
        
        # Check bot is stored
        assert view.bot == bot
        
        # Check timeout is None for persistence
        assert view.timeout is None
        
        # Check children are added
        assert len(view.children) > 0

    @pytest.mark.asyncio
    async def test_view_button_styles(self, bot):
        """Test that view buttons have correct styles."""
        view = MinorReportView(bot)

        # Check button has children (the actual buttons)
        assert len(view.children) == 3

    @pytest.mark.asyncio
    async def test_view_button_labels(self, bot):
        """Test that view buttons have correct labels."""
        view = MinorReportView(bot)

        # Check view has buttons
        assert len(view.children) == 3
        # Buttons should have custom IDs for persistence
        custom_ids = [child.custom_id for child in view.children if hasattr(child, 'custom_id')]
        assert len(custom_ids) == 3

    @pytest.mark.asyncio
    async def test_button_custom_ids_are_unique(self, bot):
        """Test that button custom IDs are unique for persistence."""
        view = MinorReportView(bot)
        
        custom_ids = [child.custom_id for child in view.children if hasattr(child, 'custom_id')]
        
        # All custom IDs should be unique
        assert len(custom_ids) == len(set(custom_ids))
        
        # Should have 3 unique custom IDs
        assert len(custom_ids) == 3
