#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json, shutil, subprocess, re, hashlib

HERE = Path(__file__).resolve().parent
WORK = HERE / "migration-workspace"
PORT = WORK / "port-1.4.61V1"
SRC = PORT / "source" / "Mage.Client" / "src" / "main" / "java" / "mage" / "client" / "cards" / "DragCardGrid.java"
POM = PORT / "source" / "Mage.Client" / "pom.xml"
MAVEN = PORT / "tools" / "apache-maven-3.9.16" / "bin" / "mvn.cmd"

OUT = WORK / "printing-selector-port-source-v6-exact-old"
REPORT = OUT / "PRINTING_SELECTOR_PORT_SOURCE_V6_EXACT_OLD.json"
SUMMARY = OUT / "RESUMEN_PRINTING_SELECTOR_PORT_SOURCE_V6_EXACT_OLD.txt"

MARK_V6 = "XCP_PRINTING_SELECTOR_V6_EXACT_OLD"

IMPORTS = [
    "import mage.cards.ExpansionSet;",
    "import mage.cards.Sets;",
    "import org.mage.plugins.card.images.ImageCache;",
    "import javax.swing.event.DocumentEvent;",
    "import javax.swing.event.DocumentListener;",
]

METHOD_V6 = r'''
    // XCP_PRINTING_SELECTOR_V6_EXACT_OLD_START
    private void chooseEdition(CardView clickedCard) {
        if (this.mode != Constants.DeckEditorMode.FREE_BUILDING || clickedCard == null) {
            return;
        }

        CardCriteria criteria = new CardCriteria();
        criteria.name(clickedCard.getName());

        java.util.List<CardInfo> printings =
                new ArrayList<>(CardRepository.instance.findCards(criteria));

        printings.sort(
                Comparator.comparing(
                        CardInfo::getSetCode,
                        Comparator.nullsLast(String::compareToIgnoreCase)
                )
                .thenComparingInt(this::xcpPrintingSelectorNumberSort)
                .thenComparing(
                        CardInfo::getCardNumber,
                        Comparator.nullsLast(String::compareToIgnoreCase)
                )
        );

        if (printings.isEmpty()) {
            JOptionPane.showMessageDialog(
                    this,
                    "No se encontraron ediciones para " + clickedCard.getName()
            );
            return;
        }

        DefaultListModel<CardInfo> model = new DefaultListModel<>();
        printings.forEach(model::addElement);

        JList<CardInfo> list = new JList<>(model);
        list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        list.setVisibleRowCount(Math.min(12, printings.size()));
        list.setFixedCellHeight(42);

        list.setCellRenderer(new DefaultListCellRenderer() {
            @Override
            public Component getListCellRendererComponent(
                    JList<?> listComponent,
                    Object value,
                    int index,
                    boolean isSelected,
                    boolean cellHasFocus
            ) {
                JLabel label = (JLabel) super.getListCellRendererComponent(
                        listComponent,
                        value,
                        index,
                        isSelected,
                        cellHasFocus
                );

                CardInfo info = (CardInfo) value;
                ExpansionSet expansion = Sets.findSet(info.getSetCode());
                String setName = expansion == null ? "" : expansion.getName();

                label.setText(
                        "<html><b>" + info.getSetCode() + "</b>  #"
                        + info.getCardNumber()
                        + (setName.isEmpty() ? "" : " · " + setName)
                        + "<br>" + info.getRarity()
                        + "</html>"
                );
                label.setIcon(null);
                return label;
            }
        });

        JTextField editionSearch = new JTextField();
        editionSearch.setToolTipText(
                "Busca por código o nombre de edición, por ejemplo LOR o Lorwyn"
        );

        Runnable filterPrintings = () -> {
            String query = editionSearch.getText().trim().toLowerCase(Locale.ROOT);
            model.clear();

            for (CardInfo info : printings) {
                ExpansionSet expansion = Sets.findSet(info.getSetCode());
                String setName = expansion == null ? "" : expansion.getName();

                if (query.isEmpty()
                        || String.valueOf(info.getSetCode()).toLowerCase(Locale.ROOT).contains(query)
                        || setName.toLowerCase(Locale.ROOT).contains(query)) {
                    model.addElement(info);
                }
            }

            if (!model.isEmpty()) {
                list.setSelectedIndex(0);
                list.ensureIndexIsVisible(0);
            }
        };

        editionSearch.getDocument().addDocumentListener(new DocumentListener() {
            @Override
            public void insertUpdate(DocumentEvent e) {
                filterPrintings.run();
            }

            @Override
            public void removeUpdate(DocumentEvent e) {
                filterPrintings.run();
            }

            @Override
            public void changedUpdate(DocumentEvent e) {
                filterPrintings.run();
            }
        });

        JLabel previewLabel = new JLabel("Selecciona una edición", SwingConstants.CENTER);
        previewLabel.setPreferredSize(new Dimension(230, 330));

        list.addListSelectionListener(event -> {
            if (event.getValueIsAdjusting()) {
                return;
            }

            CardInfo info = list.getSelectedValue();

            if (info == null) {
                previewLabel.setIcon(null);
                return;
            }

            try {
                CardView preview = new CardView(info.createMockCard());
                java.awt.Image image = ImageCache.getCardImage(preview, 220, 310).getImage();

                previewLabel.setText(image == null ? "Imagen no descargada" : "");
                previewLabel.setIcon(image == null ? null : new ImageIcon(image));
            } catch (Exception ex) {
                previewLabel.setText("No se pudo cargar la imagen");
                previewLabel.setIcon(null);
            }
        });

        int currentIndex = 0;

        for (int i = 0; i < printings.size(); i++) {
            CardInfo info = printings.get(i);

            if (Objects.equals(info.getSetCode(), clickedCard.getExpansionSetCode())
                    && Objects.equals(info.getCardNumber(), clickedCard.getCardNumber())) {
                currentIndex = i;
                break;
            }
        }

        list.setSelectedIndex(currentIndex);
        list.ensureIndexIsVisible(currentIndex);

        JScrollPane scroll = new JScrollPane(list);
        scroll.setPreferredSize(new Dimension(260, 500));

        JPanel listPanel = new JPanel(new BorderLayout(0, 6));
        JPanel searchPanel = new JPanel(new BorderLayout(6, 0));
        searchPanel.add(new JLabel("Buscar edición:"), BorderLayout.WEST);
        searchPanel.add(editionSearch, BorderLayout.CENTER);

        listPanel.add(searchPanel, BorderLayout.NORTH);
        listPanel.add(scroll, BorderLayout.CENTER);

        JPanel selectorPanel = new JPanel(new BorderLayout(10, 0));
        selectorPanel.add(listPanel, BorderLayout.CENTER);
        selectorPanel.add(previewLabel, BorderLayout.EAST);

        int answer = JOptionPane.showConfirmDialog(
                this,
                selectorPanel,
                "Elegir edición - " + clickedCard.getName(),
                JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE
        );

        CardInfo selected = list.getSelectedValue();

        if (answer != JOptionPane.OK_OPTION || selected == null) {
            return;
        }

        java.util.List<CardView> cardsToReplace =
                allCards.stream()
                        .filter(card -> Objects.equals(card.getName(), clickedCard.getName()))
                        .collect(java.util.stream.Collectors.toCollection(ArrayList::new));

        java.util.List<CardView> cardsToRemove = new ArrayList<>();

        for (CardView currentCard : cardsToReplace) {
            Card replacement = selected.createMockCard();
            CardView replacementView = new CardView(replacement);

            if (!currentCard.isSameCardVersion(replacementView)) {
                addCardView(replacementView, replacement, currentCard);
                cardsToRemove.add(currentCard);
            }
        }

        removeCards(cardsToRemove);
    }

    private int xcpPrintingSelectorNumberSort(CardInfo info) {
        String number = info.getCardNumber();

        if (number == null) {
            return Integer.MAX_VALUE;
        }

        Matcher matcher = Pattern.compile("\\d+").matcher(number);

        if (matcher.find()) {
            try {
                return Integer.parseInt(matcher.group());
            } catch (NumberFormatException ignored) {
                return Integer.MAX_VALUE;
            }
        }

        return Integer.MAX_VALUE;
    }
    // XCP_PRINTING_SELECTOR_V6_EXACT_OLD_END
'''

def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, cwd):
    print("$ " + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return cp.returncode, cp.stdout

def ensure_imports(text):
    changed = False
    for imp in IMPORTS:
        if imp in text:
            continue
        matches = list(re.finditer(r"^import .+;$", text, flags=re.MULTILINE))
        require(matches, "No import section found in DragCardGrid.java")
        pos = matches[-1].end()
        text = text[:pos] + "\n" + imp + text[pos:]
        changed = True
    return text, changed

def ensure_menu(text):
    menu_decl = 'JMenuItem chooseEdition = new JMenuItem("Elegir edición...");'
    if menu_decl in text:
        return text, False

    needle = 'JMenuItem duplicateSelection = new JMenuItem("Duplicate selected cards");'
    idx = text.find(needle)
    require(idx >= 0, "Could not find Duplicate selected cards menu anchor")

    insertion = (
        'JMenuItem chooseEdition = new JMenuItem("Elegir edición...");\n'
        '            chooseEdition.addActionListener(e2 -> chooseEdition(card));\n'
        '            menu.add(chooseEdition);\n\n'
        '            '
    )
    return text[:idx] + insertion + text[idx:], True

def remove_selector_blocks(text):
    removed = 0
    versions = ["V1", "V2", "V3", "V4", "V5", "V6_EXACT_OLD"]

    for version in versions:
        pat = re.compile(
            r"\s*// XCP_PRINTING_SELECTOR_" + re.escape(version)
            + r"_START.*?// XCP_PRINTING_SELECTOR_" + re.escape(version)
            + r"_END\s*",
            re.DOTALL
        )
        text, n = pat.subn("\n", text)
        removed += n

    while "private void chooseEdition(CardView" in text:
        start = text.find("private void chooseEdition(CardView")
        helper = text.find("private int xcpPrintingSelectorNumberSort(CardInfo info)", start)
        if helper < 0:
            break

        brace = text.find("{", helper)
        if brace < 0:
            break

        depth = 0
        end = -1
        for i in range(brace, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end < 0:
            break

        text = text[:start] + "\n" + text[end:]
        removed += 1

    return text, removed

def find_add_card_view_anchor(text):
    patterns = [
        r"(?m)^\s*public\s+void\s+addCardView\s*\(\s*final\s+CardView\s+newView\s*\)\s*\{",
        r"(?m)^\s*public\s+void\s+addCardView\s*\(\s*CardView\s+newView\s*\)\s*\{",
        r"(?m)^\s*public\s+void\s+addCardView\s*\(",
    ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.start()
    return -1

def main():
    print("=== XMage Community Patch - PRINTING SELECTOR PORT SOURCE V6 EXACT OLD ===")
    print("SAFE MODE: isolated 1.4.61V1 source only. Active XMage is NOT modified.")
    print()

    require(SRC.is_file(), f"DragCardGrid.java not found: {SRC}")
    require(POM.is_file(), f"Mage.Client pom.xml not found: {POM}")

    OUT.mkdir(parents=True, exist_ok=True)
    backups = OUT / "backups"
    backups.mkdir(parents=True, exist_ok=True)

    original = SRC.read_text(encoding="utf-8", errors="replace")
    before_hash = sha256_file(SRC)

    backup = backups / (
        "DragCardGrid.java.before-selector-v6-exact-old_"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + ".bak"
    )
    shutil.copy2(SRC, backup)

    patched, imports_changed = ensure_imports(original)
    patched, menu_changed = ensure_menu(patched)
    patched, removed_blocks = remove_selector_blocks(patched)

    idx = find_add_card_view_anchor(patched)
    require(idx >= 0, "Could not find addCardView method signature for V6 insertion")

    patched = patched[:idx] + METHOD_V6 + "\n" + patched[idx:]
    SRC.write_text(patched, encoding="utf-8")

    current = SRC.read_text(encoding="utf-8", errors="replace")
    require(MARK_V6 in current, "V6 marker missing after patch")
    require(current.count("private void chooseEdition(CardView clickedCard)") == 1,
            "Expected exactly one V6 chooseEdition method")
    require(current.count("ImageCache.getCardImage(preview, 220, 310).getImage()") == 1,
            "Exact old ImageCache preview call missing")
    require(current.count("allCards.stream()") >= 1,
            "Exact old allCards replacement source missing")
    require(current.count("private int xcpPrintingSelectorNumberSort(CardInfo info)") == 1,
            "Expected exactly one selector number-sort helper")

    after_hash = sha256_file(SRC)

    print("[OK] V6 exact-old selector source patched")
    print(f"[OK] Old selector blocks removed: {removed_blocks}")
    print(f"[OK] Backup: {backup}")
    print("[STEP] Building Mage.Client with Maven...")

    mvn_cmd = str(MAVEN) if MAVEN.is_file() else "mvn"
    rc, log = run(
        [mvn_cmd, "-pl", "Mage.Client", "-am", "-DskipTests", "package"],
        PORT / "source"
    )

    build_log = OUT / "PRINTING_SELECTOR_PORT_SOURCE_V6_EXACT_OLD_BUILD.log"
    build_log.write_text(log, encoding="utf-8", errors="replace")
    require(rc == 0, f"Maven build failed. See: {build_log}")

    target_jar = PORT / "source" / "Mage.Client" / "target" / "mage-client-1.4.61.jar"
    require(target_jar.is_file(), f"Built client jar missing: {target_jar}")

    candidate = OUT / "mage-client-1.4.61-XCP_PRINTING_SELECTOR_V6_EXACT_OLD.jar"
    shutil.copy2(target_jar, candidate)
    candidate_sha = sha256_file(candidate)

    report = {
        "schema": 6,
        "phase": "PRINTING_SELECTOR_PORT_SOURCE_V6_EXACT_OLD",
        "status": "SOURCE_PATCHED_AND_CLIENT_BUILT_NOT_ACTIVATED",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(SRC),
        "source_backup": str(backup),
        "source_sha256_before": before_hash,
        "source_sha256_after": after_hash,
        "imports_changed": imports_changed,
        "menu_changed": menu_changed,
        "removed_old_selector_blocks": removed_blocks,
        "candidate_jar": str(candidate),
        "candidate_sha256": candidate_sha,
        "build_log": str(build_log),
        "active_xmage_modified": False,
        "behavior_restored": {
            "preview_engine": "ImageCache.getCardImage(CardView,220,310).getImage()",
            "preview_widget": "JLabel + ImageIcon",
            "replacement_source": "allCards filtered by exact card name",
            "replace_all_same_name_copies": True,
            "skip_already_selected_printing": True,
            "filter_by_set_code_or_set_name": True
        },
        "next_gate": "PRINTING_SELECTOR_STATIC_SMOKE_V6_EXACT_OLD"
    }

    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    SUMMARY.write_text(
        "XMage Community Patch - PRINTING SELECTOR PORT SOURCE V6 EXACT OLD\n"
        "=================================================================\n\n"
        "RESULT: PASS\n"
        "Status: SOURCE_PATCHED_AND_CLIENT_BUILT_NOT_ACTIVATED\n"
        "Preview engine: ImageCache.getCardImage(CardView,220,310).getImage()\n"
        "Preview widget: JLabel + ImageIcon\n"
        "Replacement source: allCards filtered by exact card name\n"
        "Replace all same-name copies: YES, automatic\n"
        "Skip cards already using chosen printing: YES\n"
        "Filter by set code/name: YES\n"
        f"Old selector blocks removed: {removed_blocks}\n"
        f"Source backup: {backup}\n"
        f"Candidate jar: {candidate}\n"
        f"Candidate SHA-256: {candidate_sha}\n"
        f"Build log: {build_log}\n"
        "Active XMage modified: NO\n"
        "Next gate: PRINTING_SELECTOR_STATIC_SMOKE_V6_EXACT_OLD\n",
        encoding="utf-8"
    )

    print()
    print("=== PRINTING SELECTOR PORT SOURCE V6 EXACT OLD PASSED ===")
    print("Exact old selector behavior compiled for 1.4.61V1.")
    print("Active XMage was NOT modified.")
    print(f"Candidate: {candidate}")
    print(f"Summary: {SUMMARY}")
    input("Press Enter to close...")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print(f"ERROR: {exc}")
        print("V6 EXACT OLD FAILED. Active XMage was NOT modified.")
        input("Press Enter to close...")
        raise SystemExit(1)
