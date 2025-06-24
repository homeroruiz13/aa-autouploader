// Disable warning dialogs at the start
app.preferences.setBooleanPreference("ShowExternalJSXWarning", false);
app.preferences.setBooleanPreference("ShowScriptingWarning", false);
app.preferences.setBooleanPreference("ShowMissingFontWarning", false);
app.preferences.setBooleanPreference("ShowMissingGlyphWarning", false);
app.preferences.setBooleanPreference("ShowUpdateEditsWarning", false);
app.preferences.setBooleanPreference("ShowMissingProfileWarning", false);
app.preferences.setBooleanPreference("ShowRasterizeWarning", false);
app.preferences.setBooleanPreference("ShowProportionalScalingWarning", false);
app.preferences.setBooleanPreference("ShowTransformAgainWarning", false);
app.preferences.setBooleanPreference("ShowPasteWarning", false);
app.preferences.setBooleanPreference("ShowExportWarning", false);
app.preferences.setBooleanPreference("ShowSaveWarning", false);
app.preferences.setBooleanPreference("ShowCloseWarning", false);

// Initialize PlugPlug system
try {
    if (typeof PlugPlugSetup === 'function') {
        PlugPlugSetup();
    }
} catch(e) {
    // Ignore PlugPlug errors as they don't affect core functionality
} 