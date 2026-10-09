#!/usr/bin/env python3
"""Détoure le sujet de avatar.png (Vision, macOS 14+) -> avatar_cutout.png (RGBA). À relancer si la photo change."""
import Vision, Quartz, Foundation
from Quartz import CIImage, CIContext
import objc, sys

src = Foundation.NSURL.fileURLWithPath_("avatar.png")
handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(src, None)
req = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
ok, err = handler.performRequests_error_([req], None)
if not ok or not req.results():
    sys.exit(f"échec Vision: {err}")
obs = req.results()[0]
buf, err = obs.generateMaskedImageOfInstances_fromRequestHandler_croppedToInstancesExtent_error_(obs.allInstances(), handler, False, None)
ci = CIImage.imageWithCVPixelBuffer_(buf)
ctx = CIContext.context()
out = Foundation.NSURL.fileURLWithPath_("avatar_cutout.png")
ok, err = ctx.writePNGRepresentationOfImage_toURL_format_colorSpace_options_error_(
    ci, out, Quartz.kCIFormatRGBA8, Quartz.CGColorSpaceCreateWithName(Quartz.kCGColorSpaceSRGB), {}, None) if hasattr(ctx, "writePNGRepresentationOfImage_toURL_format_colorSpace_options_error_") else (False, None)
print("ok" if ok else f"écriture échouée: {err}")
