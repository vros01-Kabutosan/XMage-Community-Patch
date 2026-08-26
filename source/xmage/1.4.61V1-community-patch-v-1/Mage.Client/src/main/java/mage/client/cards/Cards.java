 package mage.client.cards;

 import mage.abilities.icon.CardIconRenderSettings;
 import mage.cards.MageCard;
 import mage.client.dialog.PreferencesDialog;
 import mage.client.plugins.adapters.MageActionCallback;
 import mage.client.plugins.impl.Plugins;
 import mage.client.util.CardsViewUtil;
 import mage.client.util.ClientDefaultSettings;
 import mage.client.util.GUISizeHelper;
 import mage.constants.Zone;
 import mage.util.DebugUtil;
 import mage.view.*;
 import org.apache.log4j.Logger;

 import javax.swing.*;
 import javax.swing.border.Border;
 import javax.swing.border.EmptyBorder;
 import java.awt.*;
 import java.util.*;

 /**
  * GUI: panel for stack and hand zones, component for lookAt and reveal windows (CardInfoWindowDialog)
  *
  * @author BetaSteward_at_googlemail.com, JayDi85
  */
 public class Cards extends javax.swing.JPanel {

     private static final Logger logger = Logger.getLogger(Cards.class);
     private static final Border EMPTY_BORDER = new EmptyBorder(0, 0, 0, 0);

     private final Map<UUID, MageCard> cards = new LinkedHashMap<>();
     private boolean dontDisplayTapped = false;
     private Zone zone;
     private int lastLoadedCardsCount = 0;
     private final JScrollPane parentScrollPane;

     /**
      * Defines whether component should be visible whenever there is no objects
      * within. True by default.
      */
     private boolean isVisibleIfEmpty = true;

     private Dimension cardDimension;

    // XCP_VERTICAL_STACK_LAYOUT_V2_START
    private boolean verticalStackLayout = false;

    public void setVerticalStackLayout(boolean enabled) {
        this.verticalStackLayout = enabled;

        if (jScrollPane1 != null) {
            jScrollPane1.setVerticalScrollBarPolicy(
                    enabled
                            ? ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED
                            : ScrollPaneConstants.VERTICAL_SCROLLBAR_NEVER
            );
            jScrollPane1.setHorizontalScrollBarPolicy(
                    enabled
                            ? ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER
                            : ScrollPaneConstants.HORIZONTAL_SCROLLBAR_AS_NEEDED
            );
        }

        layoutCards();
        sizeCards(getCardDimension());
        revalidate();
        repaint();
    }

    public boolean isVerticalStackLayout() {
        return verticalStackLayout;
    }

    private int getVerticalStackStep() {
        return Math.max(38, Math.min(58, getCardDimension().height / 5));
    }
    // XCP_VERTICAL_STACK_LAYOUT_V2_END


     /**
      * Creates new form Cards
      */
     public Cards() {
         this(false, null);
     }

     /**
      *
      * @param skipAddingScrollPane use parent scrolls instead own
      * @param parentScrollPane
      */
     public Cards(boolean skipAddingScrollPane, JScrollPane parentScrollPane) {
         initComponents(skipAddingScrollPane);
         setOpaque(false);
         setBackgroundColor(new Color(0, 0, 0, 100));

         // scrollpane can be own or from parent
         this.parentScrollPane = parentScrollPane;
         if (!skipAddingScrollPane) {
             jScrollPane1.setOpaque(false);
             jScrollPane1.getViewport().setOpaque(false);
             jScrollPane1.setBorder(EMPTY_BORDER);
         }

         if (Plugins.instance.isCardPluginLoaded()) {
             cardArea.setLayout(null);
         }
         cardArea.setBorder(EMPTY_BORDER);

         if (DebugUtil.GUI_GAME_DRAW_HAND_AND_STACK_BORDER) {
             setBorder(BorderFactory.createLineBorder(Color.green));
             cardArea.setBorder(BorderFactory.createLineBorder(Color.yellow));
         }

         setGUISize();
     }

     public void cleanUp() {
     }

     public void changeGUISize() {
         setGUISize();
         for (MageCard mageCard : cards.values()) {
             mageCard.setCardBounds(0, 0, getCardDimension().width, getCardDimension().height);
             mageCard.updateArtImage();
             mageCard.doLayout();
         }
         layoutCards();
         sizeCards(getCardDimension());
     }

     private void setGUISize() {
         if (jScrollPane1 != null) {
             jScrollPane1.getVerticalScrollBar().setPreferredSize(new Dimension(GUISizeHelper.scrollBarSize, 0));
             jScrollPane1.getHorizontalScrollBar().setPreferredSize(new Dimension(0, GUISizeHelper.scrollBarSize));
             jScrollPane1.getHorizontalScrollBar().setUnitIncrement(GUISizeHelper.getCardsScrollbarUnitInc(getCardDimension().width));
         }
     }

     /**
      * Sets components background color
      *
      * @param color
      */
     public void setBackgroundColor(Color color) {
         setBackground(color);
         cardArea.setOpaque(true);
         cardArea.setBackground(color);
     }

     public void setVisibleIfEmpty(boolean isVisibleIfEmpty) {
         this.isVisibleIfEmpty = isVisibleIfEmpty;
     }

     @Override
     public void setBorder(Border border) {
         super.setBorder(border);
         if (jScrollPane1 != null) {
             jScrollPane1.setViewportBorder(border);
             jScrollPane1.setBorder(border);
         }
     }

     public boolean loadCards(CardsView cardsView, BigCard bigCard, UUID gameId, boolean revertOrder) {
         boolean changed = false;

         // auto-move scrollbars to the end of the list
         boolean moveScrollbar;
         if (zone == Zone.HAND) {
             // hand moves on new cards only
             moveScrollbar = lastLoadedCardsCount != 0 && cardsView.size() > lastLoadedCardsCount;
         } else {
             // stack moves on any changes (e.g. show current stack object)
             moveScrollbar = cardsView.size() != lastLoadedCardsCount;
         }
         this.lastLoadedCardsCount = cardsView.size();

         // remove objects no longer to display
         changed = removeOutdatedCards(cardsView);

         // Workaround for bug leaving display of objects on the stack (issue #213 https://github.com/magefree/mage/issues/213)
         if (cardsView.isEmpty() && countCards() > 0) {
             // problem happens with transformable cards
             logger.fatal("Card object on the cards panel was not removed");
             for (Component comp : cardArea.getComponents()) {
                 if (comp instanceof MageCard) {
                     MageCard mageCard = (MageCard) comp;
                     logger.fatal("MageCard name:" + mageCard.getName() + " toolTiptext:" + mageCard.getToolTipText());
                 } else {
                     logger.fatal("Unknown object:" + comp.getName() + " className:" + comp.getClass().getName());
                 }
                 cardArea.remove(comp);
             }
         }

         java.util.List<CardView> orderedList = new ArrayList<>();
        java.util.List<UUID> verticalStackOrder = verticalStackLayout ? new ArrayList<>() : null;

        if (revertOrder && !verticalStackLayout) {
            // order objects for display in legacy non-stack windows
            for (CardView card : cardsView.values()) {
                orderedList.add(0, card);
            }
        } else {
            // XCP_STACK_ORDER_R5_1C
            // The real game stack is already LIFO: newest / next-to-resolve first.
            // Do not invert it for the floating vertical stack.
            orderedList.addAll(cardsView.values());
        }

        // add objects to the panel
         for (CardView card : orderedList) {
             if (dontDisplayTapped) {
                 if (card instanceof PermanentView) {
                     ((PermanentView) card).overrideTapped(false);
                 }
             }
             if (card instanceof StackAbilityView) {
                 // replace ability by original card
                 CardView tmp = ((StackAbilityView) card).getSourceCard();
                 // sync settings
                 tmp.overrideRules(card.getRules());
                 tmp.setChoosable(card.isChoosable());
                 tmp.setPlayableStats(card.getPlayableStats().copy());
                 tmp.setSelected(card.isSelected());
                 tmp.setIsAbility(true);
                 tmp.overrideTargets(card.getTargets());
                 tmp.overrideId(card.getId());
                 tmp.setAbilityType(card.getAbilityType());
                 // sync card icons
                 tmp.getCardIcons().clear();
                 tmp.getCardIcons().addAll(card.getCardIcons());
                 card = tmp;
             } else {
                 card.setAbilityType(null);
             }
             if (verticalStackOrder != null) {
                verticalStackOrder.add(card.getId());
            }

            if (!cards.containsKey(card.getId())) {
                 addCard(card, bigCard, gameId);
                 changed = true;
             }
             cards.get(card.getId()).update(card);
         }

         if (verticalStackOrder != null) {
             LinkedHashMap<UUID, MageCard> reorderedCards = new LinkedHashMap<>();
             for (UUID id : verticalStackOrder) {
                 MageCard mageCard = cards.get(id);
                 if (mageCard != null) {
                     reorderedCards.put(id, mageCard);
                 }
             }
             if (!new ArrayList<>(cards.keySet()).equals(new ArrayList<>(reorderedCards.keySet()))) {
                 changed = true;
             }
             cards.clear();
             cards.putAll(reorderedCards);
         }

         if (changed) {
             layoutCards();
         }

         if (!isVisibleIfEmpty) {
             cardArea.setVisible(!cards.isEmpty());
         }

         sizeCards(getCardDimension());
         this.revalidate();
         this.repaint();

         // auto-scroll (must use it at the end)
         if (changed && moveScrollbar) {
             SwingUtilities.invokeLater(() -> {
                 if (jScrollPane1 != null) {
                     if (verticalStackLayout) {
                        jScrollPane1.getVerticalScrollBar().setValue(
                                jScrollPane1.getVerticalScrollBar().getMinimum()
                        );
                    } else {
                        jScrollPane1.getHorizontalScrollBar().setValue(
                                jScrollPane1.getHorizontalScrollBar().getMaximum()
                        );
                    }
                 }
                 if (parentScrollPane != null) {
                     parentScrollPane.getHorizontalScrollBar().setValue(parentScrollPane.getHorizontalScrollBar().getMaximum());
                 }
             });
         }

         return changed;
     }

    public void sizeCards(Dimension cardDimension) {
        if (verticalStackLayout) {
            int count = cards.size();
            int height = (int) MageActionCallback.getHandOrStackMargins(zone).getHeight();

            if (count > 0) {
                height += cardDimension.height;
                height += (count - 1) * getVerticalStackStep();
            }

            cardArea.setPreferredSize(new Dimension(
                    (int) cardDimension.getWidth()
                            + (int) MageActionCallback.getHandOrStackMargins(zone).getWidth(),
                    Math.max(height, 1)
            ));
        } else {
            cardArea.setPreferredSize(new Dimension(
                    (int) ((cards.size()) * (cardDimension.getWidth() + MageActionCallback.getHandOrStackBetweenGapX(zone)))
                            + MageActionCallback.getHandOrStackMargins(zone).getWidth(),
                    (int) (cardDimension.getHeight())
                            + MageActionCallback.getHandOrStackMargins(zone).getHeight()
                    ));
        }

        cardArea.revalidate();
        cardArea.repaint();
    }

     public int getNumberOfCards() {
         return cards.size();
     }

     private Dimension getCardDimension() {
         if (cardDimension == null) {
             cardDimension = new Dimension(ClientDefaultSettings.dimensions.getFrameWidth(), ClientDefaultSettings.dimensions.getFrameHeight());
         }
         return cardDimension;
     }

     public void setCardDimension(Dimension dimension) {
         this.cardDimension = dimension;
         for (Component component : cardArea.getComponents()) {
             if (component instanceof MageCard) {
                 component.setBounds(0, 0, dimension.width, dimension.height);
             }
         }
         layoutCards();
     }

     private void addCard(CardView card, BigCard bigCard, UUID gameId) {
         MageCard mageCard = Plugins.instance.getMageCard(card, bigCard, new CardIconRenderSettings(), getCardDimension(), gameId, true, true, PreferencesDialog.getRenderMode(), true);
         mageCard.setCardContainerRef(cardArea);
         mageCard.update(card);
         if (zone != null) {
             mageCard.setZone(zone);
         }
         cards.put(card.getId(), mageCard);
         cardArea.add(mageCard);
         definePosition(mageCard);
     }

     private void definePosition(MageCard newCard) {
         int dx = MageActionCallback.getHandOrStackMargins(zone).getLeft(); // starting position

         // search last card's position
         for (Component currentComp : cardArea.getComponents()) {
             if (!currentComp.equals(newCard) && currentComp instanceof MageCard) {
                 MageCard currentCard = (MageCard) currentComp;
                 dx = Math.max(dx, currentCard.getCardLocation().getCardX());
             }
         }

         // Y position sets here one time only (all sorting and drag manipulations works with X)
         // add card to the end
         dx += newCard.getCardLocation().getCardWidth() + MageActionCallback.getHandOrStackBetweenGapX(newCard.getZone());
         newCard.setCardLocation(dx, MageActionCallback.getHandOrStackMargins(newCard.getZone()).getTop());
     }

     private boolean removeOutdatedCards(CardsView cardsView) {
         boolean changed = false;

         // links to components
         cards.keySet().removeIf(id -> !cardsView.containsKey(id));

         // components
         for (Component comp : cardArea.getComponents()) {
             if (comp instanceof MageCard) {
                 if (!cards.containsValue(comp)) {
                     cardArea.remove(comp);
                     changed = true;
                 }
             } else {
                 logger.error("Unknown card conponent in cards panel to remove: " + comp);
             }
         }

         return changed;
     }

     private int countCards() {
         return cardArea.getComponentCount();
     }

     /**
      * This method is called from within the constructor to initialize the form.
      * WARNING: Do NOT modify this code. The content of this method is always
      * regenerated by the Form Editor.
      */
     @SuppressWarnings("unchecked")
     // <editor-fold defaultstate="collapsed" desc="Generated Code">//GEN-BEGIN:initComponents
     private void initComponents(boolean skipAddingScrollPane) {
         setBorder(javax.swing.BorderFactory.createLineBorder(new java.awt.Color(0, 0, 0, 0)));
         setLayout(new java.awt.BorderLayout());

         cardArea = new javax.swing.JPanel();
         cardArea.setLayout(new java.awt.FlowLayout(java.awt.FlowLayout.LEFT, 0, 0));

         if (skipAddingScrollPane) {
             add(cardArea, java.awt.BorderLayout.CENTER);
         } else {
             jScrollPane1 = new javax.swing.JScrollPane();
             jScrollPane1.setVerticalScrollBarPolicy(javax.swing.ScrollPaneConstants.VERTICAL_SCROLLBAR_NEVER);
             jScrollPane1.setViewportView(cardArea);
             add(jScrollPane1, java.awt.BorderLayout.CENTER);
         }
     }// </editor-fold>//GEN-END:initComponents

     // Variables declaration - do not modify//GEN-BEGIN:variables
     private javax.swing.JPanel cardArea;
     private javax.swing.JScrollPane jScrollPane1;
     // End of variables declaration//GEN-END:variables

     public void setHScrollSpeed(int unitIncrement) {
         if (jScrollPane1 != null) {
             jScrollPane1.getHorizontalScrollBar().setUnitIncrement(unitIncrement);
         }
     }

     public void setVScrollSpeed(int unitIncrement) {
         if (jScrollPane1 != null) {
             jScrollPane1.getVerticalScrollBar().setUnitIncrement(unitIncrement);
         }
     }

    private void layoutCards() {
        if (verticalStackLayout) {
            java.util.List<MageCard> cardsToLayout = new ArrayList<>(cards.values());

            int dx = MageActionCallback.getHandOrStackMargins(zone).getLeft();
            int dy = MageActionCallback.getHandOrStackMargins(zone).getTop();
            int step = getVerticalStackStep();

            // XCP_STACK_RESOLUTION_ORDER_V4
            // loadCards(..., revertOrder=true) already exposes the stack in
            // resolution order for this container. Do NOT reverse it again:
            // index 0 is T-1 / next to resolve and must be drawn at the top.
            for (int i = 0; i < cardsToLayout.size(); i++) {
                MageCard component = cardsToLayout.get(i);
                component.setCardLocation(dx, dy);
                cardArea.setComponentZOrder(component, i);
                dy += step;
            }
            return;
        }

        java.util.List<MageCard> cardsToLayout = new ArrayList<>();
        for (Component component : cardArea.getComponents()) {
            if (component instanceof MageCard) {
                cardsToLayout.add((MageCard) component);
            }
        }

        cardsToLayout.sort(Comparator.comparingInt(cp -> cp.getCardLocation().getCardX()));

        int dx = MageActionCallback.getHandOrStackBetweenGapX(zone);
        for (MageCard component : cardsToLayout) {
            component.setCardLocation(dx, component.getCardLocation().getCardY());
            dx += component.getCardLocation().getCardWidth() + MageActionCallback.getHandOrStackBetweenGapX(zone);
        }
    }

     public void setZone(Zone zone) {
         this.zone = zone;
     }

     /**
      * For GUI: get mage card components for update (example: change playable status)
      * Warning, do not change the list
      *
      * @return
      */
     public Map<UUID, MageCard> getMageCardsForUpdate() {
         return this.cards;
     }
 }
