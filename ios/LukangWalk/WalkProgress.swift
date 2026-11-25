import Foundation

// Only counts, permanent place IDs and the voice setting can enter this file.
// The changing bundle path after an app update has no bearing on its location.
final class WalkProgress {
    private struct Values: Codable {
        var ver = 2
        var voice = true
        var drawn = 0
        var seen: [Int] = []
        var recent: [Int] = []
        var sim_drawn = 0
        var sim_seen: [Int] = []
        var sim_recent: [Int] = []
    }

    private let folder: URL
    private let file: URL
    private var values = Values()

    init() {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        folder = support.appendingPathComponent("Walk", isDirectory: true)
        file = folder.appendingPathComponent("footprints.json")
        if let data = try? Data(contentsOf: file),
           let saved = try? JSONDecoder().decode(Values.self, from: data), saved.ver == 2 {
            values = saved
        }
    }

    var initialScript: String {
        let data = try? JSONEncoder().encode(values)
        let json = data.flatMap { String(data: $0, encoding: .utf8) } ?? "{\"ver\":2}"
        return "window.lukangInitialStore = " + json + ";"
    }

    func save(_ changes: [String: Any]) throws {
        var next = values
        for (key, value) in changes {
            switch (key, value) {
            case ("voice", let enabled as Bool): next.voice = enabled
            case ("drawn", let count as Int) where count >= 0: next.drawn = count
            case ("sim_drawn", let count as Int) where count >= 0: next.sim_drawn = count
            case ("seen", let ids as [Int]): next.seen = ids
            case ("sim_seen", let ids as [Int]): next.sim_seen = ids
            case ("recent", let ids as [Int]): next.recent = Array(ids.prefix(12))
            case ("sim_recent", let ids as [Int]): next.sim_recent = Array(ids.prefix(12))
            default: return
            }
        }
        // Retain the latest state in memory so a later successful write can also save a failed one.
        values = next
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        var localFolder = folder
        var attributes = URLResourceValues()
        attributes.isExcludedFromBackup = true
        try localFolder.setResourceValues(attributes)
        try JSONEncoder().encode(next).write(to: file, options: .atomic)
    }
}
