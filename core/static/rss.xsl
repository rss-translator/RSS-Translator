<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/">
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en" dir="ltr">
            <head>
                <title><xsl:value-of select="/rss/channel/title"/> RSS Feed</title>
                <meta charset="UTF-8" />
                <meta http-equiv="x-ua-compatible" content="IE=edge,chrome=1" />
                <meta http-equiv="content-language" content="en_US" />
                <meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1,shrink-to-fit=no" />
                <meta name="referrer" content="none" />
                <!-- FAVICONS CAN GO HERE -->
                <style type="text/css">
                    body {
                        color: #222;
                        font-family: "Segoe UI", apple-system, BlinkMacSystemFont, Futura, Roboto, Arial, system-ui, sans-serif;
                    }
                    .container {
                        align-item: center;
                        display: flex;
                        justify-content: center;
                    }
                    .item {
                        max-width: 768px;
                    }
                    a {
                        color: #4166f5;
                        text-decoration: none;
                    }
                    a:visited {
                        color: #3f00ff;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="item">
                        <header>
                        <h1><xsl:value-of select="/atom:feed/atom:title"/></h1>

                        <p>
                            <xsl:value-of select="/atom:feed/atom:subtitle"/>
                        </p>

                        <p>
                            This is the Atom news feed for the 
                            <a><xsl:attribute name="href">
                                <xsl:value-of select="/atom:feed/atom:link[@rel='alternate']/@href | /atom:feed/atom:link[not(@rel)]/@href"/>
                            </xsl:attribute>
                            <xsl:value-of select="/atom:feed/atom:title"/></a>
                            website.
                        </p>
                            <p>
                                <xsl:value-of select="/feed/description"/>
                            </p>
                        </header>
                        <main>
                        <ul>
                            <xsl:for-each select="atom:feed/atom:entry">
                            <li>
                                <time>
                                    <xsl:value-of select="atom:published" />
                                </time> - 
                                <a hreflang="en" target="_blank">
                                    <xsl:attribute name="href">
                                        <xsl:value-of select="atom:link[@rel='alternate']/@href | atom:link[not(@rel)]/@href"/>
                                    </xsl:attribute>
                                    <xsl:value-of select="atom:title"/>
                                </a>
                                </li>
                            </xsl:for-each>
                            </ul>
                        </main>
                    </div>
                </div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>