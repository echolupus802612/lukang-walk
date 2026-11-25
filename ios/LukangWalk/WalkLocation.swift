import CoreLocation
import Foundation

// Core Location delivers delegate calls on the run loop where the manager was created (here, main).
final class WalkLocation: NSObject, CLLocationManagerDelegate {
    var onEvent: (([String: Any]) -> Void)?
    private var session: Int?
    private var manager: CLLocationManager?
    private var foreground = false
    private var lastFix = Date.distantPast
    private var headingStartedAt = Date.distantPast
    private var requestedPermission = false
    private var updating = false
    private var resumedSession = false

    func start(_ session: Int) {
        guard self.session != session else { return }
        end()
        self.session = session
        connectIfNeeded()
    }

    func stop(_ session: Int) {
        if self.session == session { end() }
    }

    func end() {
        disconnect()
        session = nil
        resumedSession = false
    }

    func setForeground(_ active: Bool) {
        guard foreground != active else { return }
        foreground = active
        if active {
            connectIfNeeded()
        } else {
            resumedSession = session != nil
            disconnect()
        }
    }

    private func disconnect() {
        manager?.delegate = nil
        manager?.stopUpdatingLocation()
        manager?.stopUpdatingHeading()
        manager = nil
        updating = false
        requestedPermission = false
    }

    private func connectIfNeeded() {
        guard foreground, session != nil, manager == nil else { return }
        let manager = CLLocationManager()
        self.manager = manager
        manager.delegate = self
        manager.activityType = .fitness
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = kCLDistanceFilterNone
        manager.pausesLocationUpdatesAutomatically = false
        manager.headingOrientation = .portrait
        headingStartedAt = Date()
        if resumedSession {
            lastFix = Date()
            emit(["type": "pause"])
            resumedSession = false
        } else {
            lastFix = .distantPast
        }
        emit(["type": "heading", "degrees": NSNull()])
        applyAuthorization(manager)
    }

    private func emit(_ fields: [String: Any]) {
        guard let session else { return }
        var event = fields
        event["session"] = session
        onEvent?(event)
    }

    private func fail(_ reason: String) {
        emit(["type": "error", "reason": reason])
        end()
    }

    private func applyAuthorization(_ manager: CLLocationManager) {
        guard self.manager === manager else { return }
        switch manager.authorizationStatus {
        case .notDetermined:
            if !requestedPermission {
                requestedPermission = true
                manager.requestWhenInUseAuthorization()
            }
        case .authorizedAlways, .authorizedWhenInUse:
            guard manager.accuracyAuthorization == .fullAccuracy else {
                fail("approximate")
                return
            }
            if !updating {
                updating = true
                manager.startUpdatingLocation()
                if CLLocationManager.headingAvailable() { manager.startUpdatingHeading() }
            }
        case .restricted, .denied:
            fail("denied")
        @unknown default:
            fail("unavailable")
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        applyAuthorization(manager)
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard self.manager === manager, updating else { return }
        let now = Date()
        for fix in locations {
            let age = now.timeIntervalSince(fix.timestamp)
            guard fix.timestamp > lastFix, (0...2).contains(age),
                  CLLocationCoordinate2DIsValid(fix.coordinate), fix.horizontalAccuracy >= 0 else { continue }
            lastFix = fix.timestamp
            let coords: [String: Any] = [
                "latitude": fix.coordinate.latitude, "longitude": fix.coordinate.longitude,
                "accuracy": fix.horizontalAccuracy, "speed": fix.speed
            ]
            emit(["type": "position", "coords": coords, "timestamp": fix.timestamp.timeIntervalSince1970 * 1000])
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateHeading heading: CLHeading) {
        guard self.manager === manager, updating else { return }
        let age = Date().timeIntervalSince(heading.timestamp)
        guard heading.timestamp >= headingStartedAt, (0...2).contains(age) else { return }
        let degrees = heading.trueHeading >= 0 ? heading.trueHeading : heading.magneticHeading
        if heading.headingAccuracy >= 0 && (0..<360).contains(degrees) {
            emit(["type": "heading", "degrees": degrees])
        } else {
            emit(["type": "heading", "degrees": NSNull()])
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        guard self.manager === manager else { return }
        // locationUnknown is recoverable. Let the page's 12-second first-fix timer govern fallback.
        switch (error as? CLError)?.code {
        case .locationUnknown: return
        case .headingFailure: emit(["type": "heading", "degrees": NSNull()])
        case .denied: fail("denied")
        default: fail("unavailable")
        }
    }
}
