# Example Tasks for Image Editing Agent

All examples use `create_image` tool. Empty `reference_images` = generate, with paths = edit.

## Generation (no references)

### Cozy Interior
```
Create a cozy coffee shop interior with warm lighting, 
wooden furniture, and plants by the window. 
Afternoon sunlight streaming in. Photorealistic.
```

### Portrait
```
Create a professional headshot of a fictional business executive:
- Middle-aged, confident expression
- Wearing a navy blue suit
- Neutral gray background
- Soft studio lighting
```

### Product Photo
```
Create a product photo for a luxury watch:
- Elegant silver watch with black dial
- Floating on dark surface with reflection
- Dramatic side lighting
```

### Fantasy Landscape
```
Create an epic fantasy landscape:
- Floating islands in a purple twilight sky
- Waterfalls cascading into clouds below
- Ancient ruins covered in glowing vegetation
```

## Editing (with references)

Place source images in `workspace/input/` then:

### Background Change
```
Edit workspace/input/portrait.jpg:
- Change the background to a professional office setting
- Improve lighting to be more flattering
- Keep the subject unchanged
```

### Style Transfer
```
Transform workspace/input/photo.jpg to look like:
- A watercolor painting with soft edges
- Muted pastel color palette
- Visible brush strokes
```

### Multi-Reference Composite
```
Combine workspace/input/landscape.jpg and workspace/input/building.jpg:
- Use the landscape as background
- Place the building naturally in the scene
- Match lighting and color grading
```
