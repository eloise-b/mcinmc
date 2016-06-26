from __future__ import print_function, division
import scipy.ndimage as nd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import radmc3dPy as r3
import astropy.io.fits as pyfits
import opticstools as ot
import pdb
import os
from os.path import exists
#from image_script import *
#Have plt.ion commented out so that the code doesn't generate the image windows and just 
#writes the images directly to file, this should make the code run for a shorter time
#plt.ion()

#-------------------------------------------------------------------------------------
def rotate_and_fit(im, p,cal_ims_ft,tgt_ims,model_type, model_chi_txt='',plot_ims=True):
    """Rotate a model image, and find the best fit. Output (for now!) 
    goes to file in the current directory.
    
    Parameters
    ----------
    im: numpy array
        The image from radMC3D, which has double the sampling of the data.
    p: float
        Position angle that we will rotate the RADMC image by
    cal_ims_ft: numpy complex array
        Fourier transform of our PSF image libaray
    tgt_ims: numpy array
        Target images to fit to.
            
    """
    #Set constants    
    pixel_std = 300.0 #Rough pixel standard deviation

    mod_sz = im.shape[0]
    sz = tgt_ims.shape[1]
    ntgt = tgt_ims.shape[0]
    ncal = cal_ims_ft.shape[0]
    
    #dir_p = 'pa_' + str(p)
    #exist = exists(dir_p)
    #decide whether to make the directory
    #if not exist:
    #    print("Making directory (pa)")
        #make the directory
    #    os.makedirs(dir_p)    
    #change into the new pa directory
    #os.chdir(dir_p)    
    
    #-------------------------------------------------
    # Do the rotation for each PA
    
    rotated_image = nd.interpolation.rotate(im, p, reshape=False, order=1)
    #Chop out the central part. Note that this assumes that mod_sz is larger than 2*sz.
    rotated_image = rotated_image[mod_sz/2 - sz:mod_sz/2 + sz,mod_sz/2 - sz:mod_sz/2 + sz]
    #rotated_image = ot.rebin(rotated_image, (mod_sz/2,mod_sz/2))[mod_sz/4 - sz/2:mod_sz/4 + sz/2,mod_sz/4 - sz/2:mod_sz/4 + sz/2]
    rotated_image_ft = np.fft.rfft2(np.fft.fftshift(rotated_image))
    conv_ims = np.empty( (ncal,2*sz,2*sz) )

    #Convolve all the point-spread-function images with the model.
    for j in range(ncal):
        conv_ims[j,:,:] = np.fft.irfft2(cal_ims_ft[j]*rotated_image_ft)
     
    #Calculating the best model and chi squared    
    #Go through the target images, find the best fitting calibrator image and record the chi-sqaured.
    chi_squared = np.empty( (ntgt,ncal) )
    best_model_ims = np.empty( (ntgt,sz,sz) )
    best_chi2s = np.empty( ntgt )
    best_convs = np.empty( ntgt, dtype=np.int)
    for n in range(ntgt):
        ims_shifted = np.empty( (ncal,sz,sz) )
        #Find the peak for the target
        xypeak_tgt = np.argmax(tgt_ims[n])
        xypeak_tgt = np.unravel_index(xypeak_tgt, tgt_ims[n].shape)
        for j in range(ncal):
            #Do a dodgy shift to the peak.
            xypeak_conv = np.argmax(conv_ims[j])
            xypeak_conv = np.unravel_index(xypeak_conv, conv_ims[j].shape)
            #Shift this oversampled image to the middle.
            bigim_shifted = np.roll(np.roll(conv_ims[j],2*xypeak_tgt[0]-xypeak_conv[0],axis=0),2*xypeak_tgt[1]-xypeak_conv[1],axis=1)
            #Rebin the image.
            ims_shifted[j] = ot.rebin(bigim_shifted,(sz,sz))
            #Normalise the image
            ims_shifted[j] *= np.sum(tgt_ims[n])/np.sum(ims_shifted[j])
            #Now compute the chi-squared!
            chi_squared[n,j] = np.sum( (ims_shifted[j] - tgt_ims[n])**2/pixel_std**2 )
        #Find the best shifted calibrator image (convolved with model) and save this as the best model image for this target image.
        best_conv = np.argmin(chi_squared[n])
        best_chi2s[n] = chi_squared[n,best_conv]
        best_model_ims[n] = ims_shifted[best_conv]
        best_convs[n] = best_conv
        
        if plot_ims:
            #plot the best model images
            plt.imshow(best_model_ims[n], interpolation='nearest')
            im_name = 'model_im_' + str(n) + '.png'
            plt.savefig(im_name)
            plt.clf()
            plt.imshow(np.arcsinh(best_model_ims[n]), interpolation='nearest',cmap=cm.cubehelix, clim = (3.0,15.0))
            plt.colorbar()
            stretch_name = 'model_stretch_' + str(n) + '.png'
            plt.savefig(stretch_name)
            plt.clf()
            plt.imshow(tgt_ims[n]-best_model_ims[n], interpolation='nearest',cmap=cm.cubehelix)
            plt.colorbar()
            stretch_name = 'target-model_' + str(n) + '.png'
            plt.savefig(stretch_name)
            plt.clf()
            #generate_images(best_model_ims,n)

    #save best_chi2s
    #np.savetxt('best_chi2s.txt', best_chi2s)
    #np.savetxt('best_psfs.txt', best_convs, fmt="%d")
    #add all these chi-squared values together
    total_chi = np.sum(best_chi2s)
    chi_tot = str(total_chi)
    #Calculate the normalised chi squared
    norm_chi = total_chi/(128.*128.*ntgt)
    norm_chi = str(norm_chi)
    #----------------------------------------------------------------
    #Write the model info and chi-squareds to file
    #record sum of all the chi-squareds for this model and record it with the model type
    #write to a file with model name
    if len(model_chi_txt) > 0:
        top_layer_model_chi = '/Users/eloisebirchall/Documents/Uni/Masters/radmc-3d/IRS_48_grid/MCMC_stuff/' + model_chi_txt
        model_chi_file = open(top_layer_model_chi, 'a+')
        model_chi_file.write(model_type + str(params['pa']) +',' + chi_tot + ',' + norm_chi + '\n')
        model_chi_file.close()
    else:
        return total_chi
                         