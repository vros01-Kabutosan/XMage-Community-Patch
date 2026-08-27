package org.mage.plugins.card.info;

import java.awt.Component;
import java.awt.Toolkit;
import java.awt.Dimension;
import javax.swing.JEditorPane;
import javax.swing.SwingUtilities;
import mage.client.util.GUISizeHelper;
import mage.client.util.gui.GuiDisplayUtil;
import mage.client.util.gui.GuiDisplayUtil.TextLines;
import mage.components.CardInfoPane;
import mage.view.CardView;
import org.mage.card.arcane.UI;

/**
 * GUI: card info pane for displaying card rules (example: text mode for popup card). Supports drawing mana symbols.
 *
 * @author nantuko
 */
public class CardInfoPaneImpl extends JEditorPane implements CardInfoPane {

    public static final int TOOLTIP_WIDTH_MIN = 260;
    // XCP_CARD_INFO_CONTEXT_POLISH_V3_V4_R2

    public static final int TOOLTIP_HEIGHT_MIN = 118;
    public static final int TOOLTIP_HEIGHT_MAX = 480;

    public static final int TOOLTIP_BORDER_WIDTH = 28;

    private int type;

    private int addWidth;
    private int addHeight;
    private boolean setSize = false;

    public CardInfoPaneImpl() {
        UI.setHTMLEditorKit(this);
        setEditable(false);
        setGUISize();
    }

    public void changeGUISize() {
        setGUISize();
        this.revalidate();
        this.repaint();
    }

    private void setGUISize() {
        addWidth = GUISizeHelper.cardTooltipLargeTextWidth;
        addHeight = GUISizeHelper.cardTooltipLargeTextHeight;
        setSize = true;
    }

    @Override
    public void setCard(final CardView card, final Component container) {
        try {
            SwingUtilities.invokeLater(() -> {
                TextLines textLines = GuiDisplayUtil.getTextLinesfromCardView(card);
                StringBuilder buffer = GuiDisplayUtil.getRulesFromCardView(card, textLines);

                // XCP_CONTEXT_TOOLTIP_FINAL_V4_R4
                setText(buffer.toString());
                setCaretPosition(0);
                resizeTooltipIfNeeded(
                        container,
                        textLines.getBasicTextLength(),
                        textLines.getLines().size()
                );
            });

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void resizeTooltipIfNeeded(Component container, int ruleLength, int rules) {
        if (container == null) {
            return;
        }

        // XCP_TOOLTIP_PARENT_SAFE_AUTOFIT_R5_2I
        // Fixed-width HTML + real preferred-height measurement.
        // Extra right safety: move tooltip inside its parent panel so the chat/card panel cannot cut letters.
        Dimension screen = Toolkit.getDefaultToolkit().getScreenSize();

        int contentWidth = 475;
        if (ruleLength > 180 || rules > 3) {
            contentWidth += 38;
        }
        if (ruleLength > 380 || rules > 6) {
            contentWidth += 48;
        }
        if (ruleLength > 650 || rules > 9) {
            contentWidth += 52;
        }
        int maxWidth = Math.max(475, Math.min(660, screen.width - 160));
        contentWidth = Math.max(475, Math.min(contentWidth, maxWidth));

        this.setPreferredSize(null);
        this.setMinimumSize(null);
        this.setSize(contentWidth, Math.max(2200, screen.height * 2));
        Dimension preferred = this.getPreferredSize();

        int naturalHeight = preferred == null ? 145 : preferred.height;
        int minHeight = 128;
        if (rules > 3 || ruleLength > 210) {
            minHeight = 148;
        }
        if (rules > 6 || ruleLength > 420) {
            minHeight = 178;
        }

        int contentHeight = Math.max(minHeight, naturalHeight + 18);
        int maxContentHeight = Math.max(260, Math.min(TOOLTIP_HEIGHT_MAX, screen.height - 175 - TOOLTIP_BORDER_WIDTH));
        contentHeight = Math.max(minHeight, Math.min(contentHeight, maxContentHeight));

        this.setPreferredSize(new Dimension(contentWidth, contentHeight));
        this.setMinimumSize(new Dimension(contentWidth, Math.min(contentHeight, minHeight)));
        this.setSize(contentWidth, contentHeight);

        int outerWidth = contentWidth + TOOLTIP_BORDER_WIDTH;
        int outerHeight = contentHeight + TOOLTIP_BORDER_WIDTH;
        container.setPreferredSize(new Dimension(outerWidth, outerHeight));
        container.setSize(outerWidth, outerHeight);

        GuiDisplayUtil.keepComponentInsideScreen(
                container.getX(),
                container.getY(),
                container
        );

        java.awt.Container parent = container.getParent();
        if (parent != null && parent.getWidth() > 0 && parent.getHeight() > 0) {
            int margin = 14;
            int x = container.getX();
            int y = container.getY();
            int safeRight = parent.getWidth() - margin;
            int safeBottom = parent.getHeight() - margin;
            if (x + container.getWidth() > safeRight) {
                x = Math.max(margin, safeRight - container.getWidth());
            }
            if (y + container.getHeight() > safeBottom) {
                y = Math.max(margin, safeBottom - container.getHeight());
            }
            if (x < margin) {
                x = margin;
            }
            if (y < margin) {
                y = margin;
            }
            container.setLocation(x, y);
        }

        type = (ruleLength > 180 || rules > 3) ? 1 : 0;
        setSize = false;
        container.validate();
        container.repaint();
    }
}
