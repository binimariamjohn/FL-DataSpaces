package com.ionos.edc.provision;


import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonTypeName;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.annotation.JsonPOJOBuilder;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.ProvisionedDataDestinationResource;
import static com.ionos.edc.schema.NextcloudSchema.*;

@JsonDeserialize(builder = NextCloudProvisionedResource.Builder.class)
@JsonTypeName("dataspaceconnector:nextcloudprovisionedresource")
public class NextCloudProvisionedResource  extends ProvisionedDataDestinationResource{
    private String urlKey;

    public String getFilePath() {
        return getDataAddress().getStringProperty(FILE_PATH);
    }

    public String getFileName() {
        return getDataAddress().getStringProperty(FILE_NAME);
    }

    public String getUrlKey() {
        return urlKey;
    }

    @JsonPOJOBuilder(withPrefix = "")
    public static class Builder
            extends ProvisionedDataDestinationResource.Builder<NextCloudProvisionedResource, Builder> {

        private Builder() {
            super(new NextCloudProvisionedResource());
            dataAddressBuilder.type(TYPE);

        }

        @JsonCreator
        public static Builder newInstance() {
            return new Builder();
        }

        public Builder filePath(String filePath) {
            dataAddressBuilder.property(FILE_PATH, filePath);
            return this;
        }

        public Builder fileName(String fileName) {
            dataAddressBuilder.property(FILE_NAME, fileName);
            return this;
        }

        public Builder urlKey(String urlKey) {
            provisionedResource.urlKey = urlKey;
            return this;
        }
    }
}