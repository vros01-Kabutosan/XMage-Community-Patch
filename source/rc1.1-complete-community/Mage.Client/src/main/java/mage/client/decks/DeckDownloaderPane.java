package mage.client.decks;

import mage.client.MageFrame;
import mage.client.MagePane;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;

/**
 * Community deck library updater UI.
 *
 * Reconstructed from XMage Community Patch RC1 and cleaned into normal source
 * form for reproducible porting to official XMage 1.4.61V1.
 */
public final class DeckDownloaderPane extends MagePane {

    private static final String DOWNLOADER_VERSION = "Decks V2.2 - 2026-08-11";

    private final JTextArea output = new JTextArea();
    private final JComboBox<String> source = new JComboBox<>(new String[]{
            "Todas las fuentes", "MTGO", "MTGGoldfish", "MTGTop8"
    });
    private final JButton update = new JButton("Actualizar decks");
    private final JButton continueButton = new JButton("Continuar / verificación completada");
    private final JButton cancelButton = new JButton("Cancelar actualización");
    private final JButton openFolder = new JButton("Abrir carpeta de decks");

    private volatile Process process;

    public DeckDownloaderPane() {
        setTitle("Descargar decks");
        setLayout(new BorderLayout(8, 8));

        JPanel header = new JPanel(new FlowLayout(FlowLayout.LEFT, 10, 8));
        header.add(new JLabel(DOWNLOADER_VERSION));
        header.add(new JLabel("Fuente:"));
        header.add(source);
        header.add(update);
        header.add(continueButton);
        header.add(cancelButton);
        header.add(openFolder);

        output.setEditable(false);
        output.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 13));
        output.setLineWrap(true);
        output.setWrapStyleWord(true);
        output.setText(
                "Decks V2 - 2026-08-11\n" +
                "Biblioteca automática de metajuego\n\n" +
                "Descarga Standard, Pioneer y Modern, conserva los mazos antiguos y añade únicamente composiciones nuevas.\n" +
                "Si Chrome solicita una verificación, resuélvela y pulsa Continuar.\n"
        );

        continueButton.setEnabled(false);
        cancelButton.setEnabled(false);

        update.addActionListener(this::startUpdate);
        continueButton.addActionListener(this::sendContinue);
        cancelButton.addActionListener(this::cancelUpdate);
        openFolder.addActionListener(this::openDeckFolder);

        add(header, BorderLayout.NORTH);
        add(new JScrollPane(output), BorderLayout.CENTER);
    }

    private Path engineDirectory() {
        Path current = Paths.get(System.getProperty("user.dir")).toAbsolutePath();
        Path direct = current.resolve("config").resolve("deck-downloader");
        if (Files.isDirectory(direct)) {
            return direct;
        }
        return current.resolve("xmage").resolve("mage-client").resolve("config").resolve("deck-downloader");
    }

    private String pythonCommand() {
        return System.getProperty("os.name", "").toLowerCase().contains("win") ? "py" : "python3";
    }

    private void startUpdate(ActionEvent event) {
        if (process != null && process.isAlive()) {
            JOptionPane.showMessageDialog(this, "Ya hay una actualización en marcha.");
            return;
        }

        Path engine = engineDirectory();
        Path script = engine.resolve("deck_library_updater.py");
        if (!Files.isRegularFile(script)) {
            JOptionPane.showMessageDialog(
                    this,
                    "No se encuentra el motor de descarga:\n" + script,
                    "Descargar decks",
                    JOptionPane.ERROR_MESSAGE
            );
            return;
        }

        String selected = String.valueOf(source.getSelectedItem());
        String selectedSource = "all";
        if ("MTGO".equals(selected) || "MTGGoldfish".equals(selected) || "MTGTop8".equals(selected)) {
            selectedSource = selected;
        }
        final String requestedSource = selectedSource;

        output.setText("Iniciando actualización...\n");
        update.setEnabled(false);
        continueButton.setEnabled(true);
        cancelButton.setEnabled(true);

        Thread worker = new Thread(() -> {
            try {
                ProcessBuilder builder = new ProcessBuilder(
                        pythonCommand(), "-u", script.toString(), "--source", requestedSource
                );
                builder.directory(engine.toFile());
                builder.redirectErrorStream(true);
                process = builder.start();

                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        append(line + "\n");
                    }
                }

                int result = process.waitFor();
                append("\nProceso terminado con código " + result + ".\n");
            } catch (Exception error) {
                append("\nERROR: " + error.getMessage() + "\n");
            } finally {
                process = null;
                SwingUtilities.invokeLater(() -> {
                    update.setEnabled(true);
                    continueButton.setEnabled(false);
                    cancelButton.setEnabled(false);
                });
            }
        }, "xmage-deck-downloader");

        worker.setDaemon(true);
        worker.start();
    }

    private void sendContinue(ActionEvent event) {
        Process active = process;
        if (active == null || !active.isAlive()) {
            return;
        }
        try {
            active.getOutputStream().write('\n');
            active.getOutputStream().flush();
            append("[Continuar enviado]\n");
        } catch (IOException error) {
            append("No se pudo enviar Continuar: " + error.getMessage() + "\n");
        }
    }

    private void cancelUpdate(ActionEvent event) {
        Process active = process;
        if (active == null || !active.isAlive()) {
            return;
        }
        try {
            Files.write(engineDirectory().resolve(".cancel-update"), new byte[]{'1'});
            cancelButton.setEnabled(false);
            append("[Cancelación solicitada; cerrando procesos...]\n");
        } catch (IOException error) {
            append("No se pudo solicitar la cancelación: " + error.getMessage() + "\n");
        }
    }

    private void openDeckFolder(ActionEvent event) {
        Path folder = engineDirectory().getParent().getParent().resolve("sample-decks").resolve("Descargados");
        try {
            Files.createDirectories(folder);
            Desktop.getDesktop().open(folder.toFile());
        } catch (Exception error) {
            JOptionPane.showMessageDialog(this, "No se pudo abrir:\n" + folder);
        }
    }

    private void append(String text) {
        SwingUtilities.invokeLater(() -> {
            output.append(text);
            output.setCaretPosition(output.getDocument().getLength());
        });
    }

    @Override
    public UUID getSortTableId() {
        return null;
    }

    @Override
    public boolean isActiveTable() {
        return false;
    }

    public static void showPane() {
        for (Component component : MageFrame.getDesktop().getComponents()) {
            if (component instanceof DeckDownloaderPane) {
                MageFrame.setActive((DeckDownloaderPane) component);
                return;
            }
        }

        DeckDownloaderPane pane = new DeckDownloaderPane();
        MageFrame.getDesktop().add(pane, JLayeredPane.DEFAULT_LAYER);
        pane.setVisible(true);
        MageFrame.setActive(pane);
    }
}
