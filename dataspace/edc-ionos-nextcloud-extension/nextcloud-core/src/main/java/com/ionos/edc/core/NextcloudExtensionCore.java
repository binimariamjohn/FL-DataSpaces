package com.ionos.edc.core;

import com.ionos.edc.nextcloudapi.NextCloudApi;
import com.ionos.edc.nextcloudapi.NextCloudImpl;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Provides;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.security.Vault;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;

@Provides(NextCloudApi.class)
@Extension(value = NextcloudExtensionCore.NAME)
public class NextcloudExtensionCore implements ServiceExtension {
    public static final String NAME = "Nextcloud";
    private static final String NEXTCLOUD_ENDPOINT_KEY = "edc.ionos.nextcloud.endpoint";
    private static final String NEXTCLOUD_USERNAME_KEY = "edc.ionos.nextcloud.username";
    private static final String NEXTCLOUD_PASSWORD_KEY = "edc.ionos.nextcloud.password";

    @Inject
    private Vault vault;

    @Inject
    private Monitor monitor;

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {

        var endpointKey = vault.resolveSecret(NEXTCLOUD_ENDPOINT_KEY);
        var usernameKey = vault.resolveSecret(NEXTCLOUD_USERNAME_KEY);
        var passwordKey = vault.resolveSecret(NEXTCLOUD_PASSWORD_KEY);


        if(endpointKey == null || usernameKey == null || passwordKey  == null) {
            monitor.warning("Couldn't connect or the vault didn't return values, falling back to ConfigMap Configuration");
            endpointKey = context.getSetting(NEXTCLOUD_ENDPOINT_KEY, NEXTCLOUD_ENDPOINT_KEY);
            usernameKey = context.getSetting(NEXTCLOUD_USERNAME_KEY, NEXTCLOUD_USERNAME_KEY);
            passwordKey = context.getSetting(NEXTCLOUD_PASSWORD_KEY, NEXTCLOUD_PASSWORD_KEY);

        }

        var  nextApi = new NextCloudImpl(endpointKey, usernameKey, passwordKey);
        monitor.info("initiate "+ NextcloudExtensionCore.NAME +" core");

        context.registerService(NextCloudApi.class, nextApi);
    }
}
