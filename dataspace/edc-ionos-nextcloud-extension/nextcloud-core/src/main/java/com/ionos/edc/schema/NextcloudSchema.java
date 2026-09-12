package com.ionos.edc.schema;

import static org.eclipse.edc.spi.constants.CoreConstants.EDC_NAMESPACE;

public interface  NextcloudSchema {
    String TYPE = "Nextcloud";
    String FILE_NAME = EDC_NAMESPACE +"fileName";
    String FILE_PATH = EDC_NAMESPACE +"filePath";
    String HTTP_RECEIVER =EDC_NAMESPACE +"receiverHttpEndpoint";
}
