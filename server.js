const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 3000;

app.use(cors());

const designerProfile = {
    name: "Manasvi M.",
    title: "Visual & UI Designer",
    location: "Creative Studio",
    bio: "Crafting digital experiences for musical brands and modern startups.",
    expertise: ["User Research", "Brand Identity", "Motion Design"],
    works: [
        { title: "Symphony App UI", category: "Mobile Design" },
        { title: "Acoustic Branding", category: "Logo Design" },
        { title: "Rhythm Dashboard", category: "Web App" }
    ]
};

app.get('/api/profile', (req, res) => {
    res.json(designerProfile);
});

app.listen(PORT, () => {
    console.log(🎨 Designer Backend running on http://localhost:${PORT});
});