# Contribute

Contributors are welcome to extend the plugin's features further. Please fork the repository and make a pull request if your feature is ready. Just creating issues also helps to maintain the plugin working. Please, provide a meaningful example.

## Translations

Translation files are placed in the folder i18n of the plugin. 

You can copy an existing .ts file and translate it to your language (sections translation). 
Please name the new file according to the following scheme: `xx.ts`, where `xx` is the [ISO 639-1 language code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) of your language (e.g. `de` for German, `es` for Spanish, `it` for Italian, etc.).
You can use [Qt Linguist](https://doc.qt.io/qt-5/qtlinguist-index.html) to translate the strings in the .ts file.

You have to create a .qm file from the .ts file after translating it. You can use the `lrelease` tool from the Qt framework to do this. The command is as follows:

```
lrelease path/to/yourfile.ts
```

After translating the strings in the .ts file and the creation of the .qm file, please create a pull request with your new translation file included in the i18n folder of the repository. This way, your translation can be included in future releases of the plugin.