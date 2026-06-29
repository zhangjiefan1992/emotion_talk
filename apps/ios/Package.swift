// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "EmotionTalkIOS",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(name: "EmotionTalkCore", targets: ["EmotionTalkCore"]),
        .executable(name: "EmotionTalkApp", targets: ["EmotionTalkApp"]),
        .executable(name: "EmotionTalkAPISmoke", targets: ["EmotionTalkAPISmoke"])
    ],
    targets: [
        .target(name: "EmotionTalkCore"),
        .executableTarget(
            name: "EmotionTalkApp",
            dependencies: ["EmotionTalkCore"]
        ),
        .executableTarget(
            name: "EmotionTalkAPISmoke",
            dependencies: ["EmotionTalkCore"]
        ),
        .testTarget(
            name: "EmotionTalkCoreTests",
            dependencies: ["EmotionTalkCore"]
        ),
        .testTarget(
            name: "EmotionTalkAppTests",
            dependencies: ["EmotionTalkApp"]
        )
    ]
)
