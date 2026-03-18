// V3: Arithmetic overflow on u64 - Instance 2 (PATCHED)
// Fix: use checked_mul and validate raw_price has an upper bound.

use anchor_lang::prelude::*;

declare_id!("ORACLE11111111111111111111111111111111111111");

// Maximum raw price accepted — prevents overflow with scale factor of 10^6.
const MAX_RAW_PRICE: u64 = u64::MAX / 1_000_000;

#[program]
pub mod price_oracle {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let oracle = &mut ctx.accounts.oracle;
        oracle.price = 0;
        oracle.scale = 6;
        oracle.bump = *ctx.bumps.get("oracle").unwrap();
        Ok(())
    }

    pub fn update_price(ctx: Context<OracleAction>, raw_price: u64) -> Result<()> {
        require!(raw_price <= MAX_RAW_PRICE, OracleError::PriceTooLarge);
        let oracle = &mut ctx.accounts.oracle;
        let scale_factor = 10u64.pow(oracle.scale as u32);
        // FIX: checked_mul returns error instead of wrapping.
        oracle.price = raw_price
            .checked_mul(scale_factor)
            .ok_or(OracleError::Overflow)?;
        Ok(())
    }

    pub fn get_liquidation_threshold(ctx: Context<OracleAction>) -> Result<u64> {
        let threshold = ctx
            .accounts
            .oracle
            .price
            .checked_mul(80)
            .ok_or(OracleError::Overflow)?
            .checked_div(100)
            .ok_or(OracleError::Overflow)?;
        Ok(threshold)
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Oracle::SIZE,
        seeds = [b"oracle"],
        bump
    )]
    pub oracle: Account<'info, Oracle>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct OracleAction<'info> {
    #[account(mut, seeds = [b"oracle"], bump = oracle.bump)]
    pub oracle: Account<'info, Oracle>,
    pub updater: Signer<'info>,
}

#[account]
pub struct Oracle {
    pub price: u64,
    pub scale: u8,
    pub bump: u8,
}

impl Oracle {
    pub const SIZE: usize = 8 + 1 + 1;
}

#[error_code]
pub enum OracleError {
    #[msg("Arithmetic overflow")]
    Overflow,
    #[msg("Raw price exceeds safe maximum")]
    PriceTooLarge,
}
