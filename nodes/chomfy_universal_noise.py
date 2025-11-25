import torch
import torch.nn.functional as F

class ChomfyUniversalNoise:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "original_latent": ("LATENT",),
                "mix_strength": ("FLOAT", {"default": 0.30, "min": 0.00, "max": 1.00, "step": 0.01}),
                "noise_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "pixel_x": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "pixel_y": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "pixel_width": ("INT", {"default": 512, "min": 0, "max": 10000}),
                "pixel_height": ("INT", {"default": 512, "min": 0, "max": 10000}),
            },
            "optional": {
                "mask_override": ("MASK",), 
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "universal_noise_mix"
    CATEGORY = "ChomfyNodes"

    def universal_noise_mix(self, original_latent, mix_strength, noise_seed, pixel_x, pixel_y, pixel_width, pixel_height, mask_override=None):
        # 1. Setup and DataType Detection
        orig_samples = original_latent["samples"].clone()
        
        # Detect exact dtype (BF16/FP32/FP16) and device (CPU/CUDA)
        # This makes it compatible with GGUF, FP8, and Standard models
        current_dtype = orig_samples.dtype
        current_device = orig_samples.device
        input_shape = orig_samples.shape
        
        # 2. Generate Noise using exact same Type/Device as input
        torch.manual_seed(noise_seed)
        noise_samples = torch.randn(input_shape, device=current_device, dtype=current_dtype)

        # 3. Create the Mix Mask
        mix_mask = torch.zeros(input_shape, device=current_device, dtype=current_dtype)
        
        # Check if we are 4D (Image) or 5D (Video/Wan)
        is_video = (len(input_shape) == 5)

        if is_video:
            batch, channels, time, max_h, max_w = input_shape
        else:
            batch, channels, max_h, max_w = input_shape

        # --- LOGIC SPLIT: Mask Input vs Box Coordinates ---
        
        if mask_override is not None:
            # A. USER PROVIDED A MASK
            # Resize mask to match latent dimensions exactly
            # Masks are usually (Batch, Height, Width), we need to match the latent shape
            
            # 1. Add channel dimension to mask: (B, H, W) -> (B, 1, H, W)
            mask_resized = mask_override.unsqueeze(1)
            
            # 2. Interpolate (Resize) mask to latent size (Latent is compressed by 8)
            # We use 'nearest' to keep hard edges if pixel art, or 'bilinear' for smooth.
            mask_resized = F.interpolate(mask_resized, size=(max_h, max_w), mode="bilinear", align_corners=False)
            
            # 3. Cast and Expand
            mask_resized = mask_resized.to(device=current_device, dtype=current_dtype)
            
            # 4. Expand to match channel count (4 for SDXL, 16 for Flux)
            if is_video:
                # For video, we repeat the mask across the time dimension
                # (B, 1, H, W) -> (B, C, T, H, W)
                mask_resized = mask_resized.unsqueeze(2) # Add time dim
                mask_resized = mask_resized.expand(-1, channels, time, -1, -1)
                mix_mask = mask_resized
            else:
                # (B, 1, H, W) -> (B, C, H, W)
                mix_mask = mask_resized.expand(-1, channels, -1, -1)

        else:
            # B. USER USED BOX COORDINATES
            scale_factor = 8
            lx = pixel_x // scale_factor
            ly = pixel_y // scale_factor
            lw = pixel_width // scale_factor
            lh = pixel_height // scale_factor

            # Bounds checking
            if lw <= 0: lw = max_w - lx
            if lh <= 0: lh = max_h - ly
            
            lx = max(0, min(lx, max_w - 1))
            ly = max(0, min(ly, max_h - 1))
            lw = max(1, min(lw, max_w - lx))
            lh = max(1, min(lh, max_h - ly))

            # Draw the box
            if is_video:
                mix_mask[:, :, :, ly:ly+lh, lx:lx+lw] = 1.0
            else:
                mix_mask[:, :, ly:ly+lh, lx:lx+lw] = 1.0

        # 4. The Universal Blend
        # Formula: Result = Original * (1 - Stren) + Noise * Stren
        effective_strength = mix_mask * mix_strength
        blended_samples = orig_samples * (1.0 - effective_strength) + noise_samples * effective_strength

        return ({"samples": blended_samples},)

NODE_CLASS_MAPPINGS = {
    "ChomfyUniversalNoise": ChomfyUniversalNoise
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ChomfyUniversalNoise": "Chomfy Universal Regional Noise"
}