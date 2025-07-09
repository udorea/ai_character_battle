<?php
require_once 'db_config.php';
setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection();

    $input = json_decode(file_get_contents('php://input'), true);

    $char1Id = $input['character1_id'] ?? null;
    $char2Id = $input['character2_id'] ?? null;
    $winnerId = $input['winner_id'] ?? null;
    $loserId = $input['loser_id'] ?? null;
    $battleReason = $input['battle_reason'] ?? null;

    if (empty($char1Id) || empty($char2Id) || empty($winnerId) || empty($loserId)) {
        echo json_encode(["success" => false, "message" => "모든 배틀 참가자 및 승패 ID는 필수입니다."]);
        exit();
    }

    $sql = "INSERT INTO battle_logs (character1_id, character2_id, winner_id, loser_id, battle_reason) VALUES (?, ?, ?, ?, ?)";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("iiiis", $char1Id, $char2Id, $winnerId, $loserId, $battleReason);

    if ($stmt->execute()) {
        echo json_encode(["success" => true, "message" => "배틀 로그가 성공적으로 저장되었습니다."]);
    } else {
        error_log("SQL Error (log_battle.php): " . $stmt->error);
        throw new Exception("배틀 로그 저장 실패: " . $stmt->error);
    }

    $stmt->close();
    $conn->close();

} catch (Exception $e) {
    echo json_encode(["success" => false, "message" => $e->getMessage()]);
}
?>
