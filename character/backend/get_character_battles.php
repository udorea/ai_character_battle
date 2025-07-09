<?php
require_once 'db_config.php';

setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection();

    $character_id = isset($_GET['id']) ? intval($_GET['id']) : 0;

    if ($character_id <= 0) {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid character ID']);
        exit();
    }

    $sql = "
        SELECT
            bl.timestamp,
            bl.battle_reason,
            c1.name AS character1_name,
            c2.name AS character2_name,
            w.name AS winner_name,
            l.name AS loser_name
        FROM battle_logs bl
        JOIN characters c1 ON bl.character1_id = c1.id
        JOIN characters c2 ON bl.character2_id = c2.id
        JOIN characters w ON bl.winner_id = w.id
        JOIN characters l ON bl.loser_id = l.id
        WHERE bl.character1_id = ? OR bl.character2_id = ?
        ORDER BY bl.timestamp DESC;
    ";
    
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("ii", $character_id, $character_id);
    $stmt->execute();
    $result = $stmt->get_result();

    $battles = [];
    while ($row = $result->fetch_assoc()) {
        $battles[] = $row;
    }

    echo json_encode($battles);

    $stmt->close();
    $conn->close();

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["error" => "Server error: " . $e->getMessage()]);
}
?>
