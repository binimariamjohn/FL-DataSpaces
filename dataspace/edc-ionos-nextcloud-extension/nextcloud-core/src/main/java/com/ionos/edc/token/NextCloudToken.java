package com.ionos.edc.token;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonTypeName;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.SecretToken;

@JsonTypeName("dataspaceconnector:nexcloudtoken")
public class NextCloudToken implements SecretToken {
    private final String urlToken;
    private Boolean downloadable;
    private final long expiration;

    public NextCloudToken(@JsonProperty("urlKey") String urlToken,@JsonProperty("downloadable") Boolean downloadable, @JsonProperty("expiration") long expiration) {
        this.urlToken = urlToken;
        this.downloadable = downloadable;
        this.expiration = expiration;
    }

    public String getUrlToken() {
        return urlToken;
    }

    public Boolean getDownloadable() {
        return downloadable;
    }

    @Override
    public long getExpiration() {
        return expiration;
    }
}
