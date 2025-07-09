<?php
require_once 'db_config.php';

setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection();
    $sql = "
        SELECT
            bl.timestamp, -- 'battle_time' 대신 'timestamp' 사용
            c_winner.name AS winner_name,
            c_loser.name AS loser_name,
            bl.battle_reason
        FROM battle_logs bl
        JOIN characters c_winner ON bl.winner_id = c_winner.id
        JOIN characters c_loser ON bl.loser_id = c_loser.id
        ORDER BY bl.timestamp DESC
        LIMIT 1;
    ";
    
    $result = $conn->query($sql);

    $latest_log = null;
    if ($result->num_rows > 0) {
        $latest_log = $result->fetch_assoc();
    }

    echo json_encode($latest_log);

    $conn->close();

} catch (Exception $e) {
    error_log("SQL Error (get_latest_battle_log.php): " . $e->getMessage());
    http_response_code(500); 
    echo json_encode(["success" => false, "message" => "Server error: " . $e->getMessage()]);
}
?>
