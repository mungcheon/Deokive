import Cocoa
import FlutterMacOS

class MainFlutterWindow: NSWindow {
  override func awakeFromNib() {
    let flutterViewController = FlutterViewController()
    let mobileSize = NSSize(width: 430, height: 932)
    let currentFrame = self.frame
    let centeredOrigin = NSPoint(
      x: currentFrame.origin.x,
      y: currentFrame.origin.y
    )
    let windowFrame = NSRect(origin: centeredOrigin, size: mobileSize)
    self.contentViewController = flutterViewController
    self.setFrame(windowFrame, display: true)
    self.minSize = NSSize(width: 390, height: 844)

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()
  }
}
