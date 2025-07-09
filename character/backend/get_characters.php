<?php
require_once 'db_config.php';
setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection();

    $sql = "SELECT id, name, description, ai_analysis, wins, losses FROM characters";
    
    if (isset($_GET['name']) && !empty($_GET['name'])) {
        $search_name = $_GET['name'];
        $sql .= " WHERE name = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("s", $search_name);
    } else {
        $stmt = $conn->prepare($sql);
    }
    
    $stmt->execute();
    $result = $stmt->get_result();

    $characters = [];
    while ($row = $result->fetch_assoc()) {
        $characters[] = $row;
    }

    echo json_encode($characters);

    $stmt->close();
    $conn->close();

} catch (Exception $e) {
    error_log("SQL Error (get_characters.php): " . $e->getMessage());
    echo json_encode(["success" => false, "message" => $e->getMessage()]);
}
?>
