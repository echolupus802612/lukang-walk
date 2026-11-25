import CoreHaptics
import UIKit
import WebKit

private let bridgeName = "lukangWalk"

// WKUserContentController retains its handlers, so it must not own the view controller.
private final class WalkMessages: NSObject, WKScriptMessageHandler {
    weak var owner: WalkViewController?

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        owner?.receive(message)
    }
}

final class WalkViewController: UIViewController, WKNavigationDelegate {
    private let location = WalkLocation()
    private let progress = WalkProgress()
    private let index = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "Web")
    private var web: WKWebView!
    private var awake = false
    private var foreground = false
    private var haptics: CHHapticEngine?

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }

    override func loadView() {
        let configuration = WKWebViewConfiguration()
        let handler = WalkMessages()
        handler.owner = self
        configuration.userContentController.add(handler, name: bridgeName)
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.allowsInlineMediaPlayback = true
        web = WKWebView(frame: .zero, configuration: configuration)
        web.navigationDelegate = self
        web.scrollView.contentInsetAdjustmentBehavior = .never
        web.isOpaque = false
        web.backgroundColor = UIColor(named: "LaunchBackground") ?? .systemBackground
        web.underPageBackgroundColor = web.backgroundColor
        view = web
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        location.onEvent = { [weak self] event in self?.send(event) }
        loadGame()
    }

    private func loadGame() {
        guard let index else {
            let label = UILabel()
            label.text = "讀不到散步吧的畫面。請重新安裝 App。"
            label.textColor = .white
            label.numberOfLines = 0
            label.textAlignment = .center
            label.frame = view.bounds.insetBy(dx: 24, dy: 0)
            label.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            view.addSubview(label)
            return
        }
        let scripts = web.configuration.userContentController
        scripts.removeAllUserScripts()
        scripts.addUserScript(WKUserScript(source: progress.initialScript,
                                           injectionTime: .atDocumentStart, forMainFrameOnly: true))
        var entry = index
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-simulate-walk") {
            var url = URLComponents(url: index, resolvingAgainstBaseURL: false)
            url?.fragment = "sim"
            entry = url?.url ?? index
        }
        #endif
        web.loadFileURL(entry, allowingReadAccessTo: index.deletingLastPathComponent())
    }

    func setForeground(_ active: Bool) {
        foreground = active
        location.setForeground(active)
        UIApplication.shared.isIdleTimerDisabled = awake && active
        if !active {
            haptics?.stop(completionHandler: nil)
            haptics = nil
        }
    }

    private func isGameURL(_ url: URL?) -> Bool {
        guard let url, let index, url.isFileURL else { return false }
        return url.standardizedFileURL.path == index.standardizedFileURL.path
    }

    fileprivate func receive(_ message: WKScriptMessage) {
        guard message.name == bridgeName, message.frameInfo.isMainFrame,
              isGameURL(message.frameInfo.request.url),
              let body = message.body as? [String: Any], let action = body["action"] as? String else { return }
        switch action {
        case "start":
            if let session = body["session"] as? Int, session > 0 { location.start(session) }
        case "stop":
            if let session = body["session"] as? Int { location.stop(session) }
        case "awake":
            guard let enabled = body["enabled"] as? Bool else { return }
            awake = enabled
            UIApplication.shared.isIdleTimerDisabled = enabled && foreground
        case "arrived":
            if foreground { playArrival() }
        case "credits":
            showCredits()
        case "store":
            let changes: [String: Any]
            if let batch = body["values"] as? [String: Any] {
                changes = batch
            } else if let key = body["key"] as? String, let value = body["value"] {
                changes = [key: value]
            } else { return }
            do {
                try progress.save(changes)
            } catch {
                send(["type": "storeError"])
            }
        default: break
        }
    }

    private func send(_ event: [String: Any]) {
        web.callAsyncJavaScript("window.dispatchEvent(new CustomEvent('lukangNative', {detail: event}));",
                                arguments: ["event": event], in: nil, in: .page, completionHandler: nil)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let allowed = navigationAction.targetFrame?.isMainFrame == true && isGameURL(navigationAction.request.url)
        decisionHandler(allowed ? .allow : .cancel)
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        location.end()
        awake = false
        UIApplication.shared.isIdleTimerDisabled = false
        loadGame()
    }

    private func playArrival() {
        guard CHHapticEngine.capabilitiesForHardware().supportsHaptics else { return }
        do {
            if haptics == nil {
                let engine = try CHHapticEngine()
                engine.playsHapticsOnly = true
                engine.isAutoShutdownEnabled = true
                haptics = engine
            }
            guard let engine = haptics else { return }
            let pulses = [
                CHHapticEvent(eventType: .hapticContinuous, parameters: [], relativeTime: 0, duration: 0.06),
                CHHapticEvent(eventType: .hapticContinuous, parameters: [], relativeTime: 0.10, duration: 0.12)
            ]
            let pattern = try CHHapticPattern(events: pulses, parameters: [])
            try engine.start()
            try engine.makePlayer(with: pattern).start(atTime: CHHapticTimeImmediate)
        } catch {
            haptics = nil
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        }
    }

    private func showCredits() {
        guard presentedViewController == nil,
              let page = Bundle.main.url(forResource: "credits", withExtension: "html", subdirectory: "Web")
        else { return }
        present(UINavigationController(rootViewController: CreditsViewController(page: page)), animated: true)
    }
}

private final class CreditsViewController: UIViewController, WKNavigationDelegate {
    private let page: URL

    init(page: URL) {
        self.page = page
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { return nil }

    override func loadView() {
        let config = WKWebViewConfiguration()
        config.defaultWebpagePreferences.allowsContentJavaScript = false
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self
        view = web
        navigationItem.title = "資料來源與授權"
        navigationItem.rightBarButtonItem = UIBarButtonItem(title: "完成", style: .done, target: self,
                                                           action: #selector(close))
        web.loadFileURL(page, allowingReadAccessTo: page.deletingLastPathComponent())
    }

    @objc private func close() { dismiss(animated: true) }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if url.isFileURL && url.standardizedFileURL.path == page.standardizedFileURL.path {
            decisionHandler(.allow)
            return
        }
        decisionHandler(.cancel)
        if navigationAction.navigationType == .linkActivated,
           let scheme = url.scheme?.lowercased(), ["https", "http"].contains(scheme) {
            UIApplication.shared.open(url)
        }
    }
}
