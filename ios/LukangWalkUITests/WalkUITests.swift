import CoreLocation
import XCTest

final class WalkUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    private func selectNear(in game: XCUIElement) {
        // WebKit exposes the HTML aria-pressed control as a switch on iOS 26.
        let near = game.descendants(matching: .any).matching(
            NSPredicate(format: "label == %@", "近 ~500m")
        ).firstMatch
        XCTAssertTrue(near.waitForExistence(timeout: 10))
        near.tap()
    }

    @MainActor
    func testCreditsOpenAndClose() {
        let app = XCUIApplication()
        app.launch()
        let game = app.webViews.firstMatch
        let credits = game.links["資料來源"]
        XCTAssertTrue(credits.waitForExistence(timeout: 20))
        credits.tap()

        let navigation = app.navigationBars["資料來源與授權"]
        let done = navigation.buttons["完成"]
        XCTAssertTrue(done.waitForExistence(timeout: 10))
        XCTAssertTrue(app.links["OpenStreetMap 著作權說明"].waitForExistence(timeout: 10))
        done.tap()
        let start = game.buttons["抽一支籤，出發"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        XCTAssertTrue(start.isHittable)
    }

    @MainActor
    func testGPSWalkUsesSimulatedCoreLocation() {
        let device = XCUIDevice.shared
        let previousLocation = device.location
        defer { device.location = previousLocation }
        let coordinate = CLLocationCoordinate2D(latitude: 24.0565, longitude: 120.4335)
        @MainActor func lukangFix() -> XCUILocation {
            XCUILocation(location: CLLocation(coordinate: coordinate, altitude: 0,
                                               horizontalAccuracy: 5, verticalAccuracy: 5, timestamp: Date()))
        }
        device.location = lukangFix()
        let app = XCUIApplication()
        app.launch()
        let game = app.webViews.firstMatch
        let start = game.buttons["抽一支籤，出發"]
        XCTAssertTrue(start.waitForExistence(timeout: 20))
        selectNear(in: game)
        device.location = lukangFix()
        start.tap()

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let permission = springboard.alerts.buttons.matching(NSPredicate(
            format: "label IN %@", ["Allow While Using App", "Allow While Using the App", "使用 App 期間允許", "使用 App 時允許"]
        )).firstMatch
        if permission.waitForExistence(timeout: 2) { permission.tap() }
        device.location = lukangFix()
        let gps = game.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "GPS")).firstMatch
        XCTAssertTrue(gps.waitForExistence(timeout: 12), "定位必須經過 Core Location 進入實走")
        XCTAssertTrue(game.buttons["換一支"].exists)
        XCTAssertFalse(game.buttons["▲ 朝籤走"].exists)
        game.buttons["收工"].tap()
        XCTAssertTrue(game.staticTexts["已收工"].waitForExistence(timeout: 5))
    }

    @MainActor
    func testSimulatedWalkPersistsDrawAfterRelaunch() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-simulate-walk"]
        app.launch()

        let game = app.webViews.firstMatch
        let status = game.staticTexts.matching(
            NSPredicate(format: "label BEGINSWITH %@", "模擬：抽過 ")
        ).firstMatch
        XCTAssertTrue(status.waitForExistence(timeout: 20))
        let previousCount = try XCTUnwrap(status.label.split(separator: " ").compactMap { Int($0) }.first)

        selectNear(in: game)
        let start = game.buttons["抽一支籤，出發"]
        start.tap()
        let forward = game.buttons["▲ 朝籤走"]
        XCTAssertTrue(forward.waitForExistence(timeout: 10))
        forward.press(forDuration: 0.6)
        game.buttons["收工"].tap()
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        let expected = "模擬：抽過 \(previousCount + 1) 支"
        XCTAssertTrue(status.label.hasPrefix(expected))

        app.terminate()
        app.launch()
        XCTAssertTrue(start.waitForExistence(timeout: 20))
        XCTAssertTrue(status.waitForExistence(timeout: 10))
        XCTAssertTrue(status.label.hasPrefix(expected), "重新啟動後的足跡：\(status.label)")
    }
}
